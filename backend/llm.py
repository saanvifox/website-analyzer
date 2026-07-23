import json
import os
import re
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_MODEL = "openai/gpt-oss-120b"


def convert_mcp_tools(
    mcp_tools: list[Any],
) -> list[dict[str, Any]]:
    allowed_tools = {
        "browser_click",
        "browser_type",
        "browser_fill_form",
        "browser_press_key",
        "browser_select_option",
        "browser_hover",
        "browser_navigate_back",
        "browser_wait_for",
        "browser_find",
        "browser_tabs",
        "browser_handle_dialog",
    }

    groq_tools: list[dict[str, Any]] = []

    for tool in mcp_tools:
        if tool.name not in allowed_tools:
            continue

        groq_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": (
                        tool.description
                        or f"Run {tool.name}"
                    ),
                    "parameters": tool.inputSchema,
                },
            }
        )

    groq_tools.append(
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": (
                    "Return the final answer when the "
                    "current website contains enough "
                    "information to complete the task."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": (
                                "A clear final answer based "
                                "only on the website."
                            ),
                        }
                    },
                    "required": ["answer"],
                    "additionalProperties": False,
                },
            },
        }
    )

    return groq_tools


def build_agent_prompt(
    task: str,
    snapshot: str,
    history: str,
) -> str:
    return f"""
You are a browser agent controlling Playwright MCP.

TASK:
{task}

CURRENT PAGE SNAPSHOT:
{snapshot}

RECENT ACTIONS:
{history}

Choose exactly one provided tool.

IMPORTANT:
- You must return a tool call, never plain text.
- Call finish when the snapshot contains enough information.
- Do not explain your reasoning.
- Do not write text before or after the tool call.

Rules:
1. Use only the provided tools.
2. Use element references exactly as shown.
3. Never invent element references, URLs, facts, or answers.
4. The current page snapshot has already been provided.
5. Prefer finish when the current page supports the answer.
6. Do not repeat a failed action without a clear reason.
7. Do not use outside knowledge.
8. Never call browser_find with empty text or an empty regex.
9. Do not navigate away from the website unless required.
10. Never repeat an action that already succeeded.
11. Select only one tool.
""".strip()


def get_retry_seconds(
    response: requests.Response,
    attempt: int,
) -> float:
    retry_after = response.headers.get("retry-after")

    if retry_after:
        try:
            return float(retry_after) + 0.5
        except ValueError:
            pass

    try:
        message = response.json()["error"]["message"]

        match = re.search(
            r"try again in\s+"
            r"(\d+(?:\.\d+)?)"
            r"(ms|s|m)",
            message,
            re.IGNORECASE,
        )

        if match:
            amount = float(match.group(1))
            unit = match.group(2).lower()

            if unit == "ms":
                return amount / 1000 + 0.5

            if unit == "m":
                return amount * 60 + 0.5

            return amount + 0.5

    except (
        ValueError,
        KeyError,
        TypeError,
    ):
        pass

    return 3.0 + attempt


def send_groq_request(
    request_body: dict[str, Any],
    api_key: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    for attempt in range(max_retries):
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": (
                        f"Bearer {api_key}"
                    ),
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=90,
            )

        except requests.RequestException as error:
            raise RuntimeError(
                f"Could not connect to Groq: {error}"
            ) from error

        if response.ok:
            try:
                return response.json()
            except ValueError as error:
                raise RuntimeError(
                    "Groq returned invalid JSON: "
                    f"{response.text}"
                ) from error

        if response.status_code != 429:
            raise RuntimeError(
                "Groq API failed with HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )

        print("========== GROQ 429 ==========")
        print(response.text)
        print("Headers:")
        print(dict(response.headers))
        print("==============================")

        if attempt == max_retries - 1:
            break

        wait_seconds = get_retry_seconds(
            response,
            attempt,
        )

        print(
            "Groq rate limit reached. "
            f"Waiting {wait_seconds:.1f} seconds..."
        )

        time.sleep(wait_seconds)

    raise RuntimeError(
        "Groq rate limit remained active "
        "after all retry attempts."
    )


def parse_tool_call(
    data: dict[str, Any],
) -> dict[str, Any]:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            "Groq response did not contain a message: "
            f"{data}"
        ) from error

    tool_calls = message.get("tool_calls") or []

    if not tool_calls:
        content = message.get("content")

        # Safety fallback. This should rarely happen because
        # tool_choice is required.
        if isinstance(content, str) and content.strip():
            return {
                "name": "finish",
                "arguments": {
                    "answer": content.strip(),
                },
            }

        raise RuntimeError(
            "Groq returned neither a tool call "
            f"nor an answer: {data}"
        )

    try:
        function = tool_calls[0]["function"]
        function_name = function["name"]
        raw_arguments = function.get(
            "arguments",
            "{}",
        )

        if isinstance(raw_arguments, str):
            arguments = json.loads(raw_arguments)

        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments

        else:
            raise TypeError(
                "Tool arguments must be a JSON "
                "string or dictionary."
            )

        if not isinstance(arguments, dict):
            raise TypeError(
                "Decoded tool arguments must "
                "be a dictionary."
            )

        return {
            "name": function_name,
            "arguments": arguments,
        }

    except (
        KeyError,
        IndexError,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        raise RuntimeError(
            "Groq returned an invalid tool call: "
            f"{tool_calls[0]}"
        ) from error


def ask_llm(
    task: str,
    snapshot: str,
    history: str,
    groq_tools: list[dict[str, Any]],
) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing."
        )

    if not groq_tools:
        raise RuntimeError(
            "No tools were provided to Groq."
        )

    prompt = build_agent_prompt(
        task,
        snapshot,
        history,
    )

    request_body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "tools": groq_tools,

        # Every valid response is a tool call,
        # including the custom finish tool.
        "tool_choice": "required",

        "temperature": 0,
        "reasoning_effort": "low",

        # 200 was too small for GPT-OSS reasoning
        # plus the final function call.
        "max_completion_tokens": 1000,
    }

    data = send_groq_request(
        request_body,
        api_key,
    )

    usage = data.get("usage", {})

    if usage:
        print(
            "Groq token usage:",
            f'prompt={usage.get("prompt_tokens", 0)},',
            f'completion='
            f'{usage.get("completion_tokens", 0)},',
            f'total={usage.get("total_tokens", 0)}',
        )

    selected = parse_tool_call(data)

    print(
        "Groq selected:",
        selected["name"],
        selected["arguments"],
    )

    return selected