import json
import os
import textwrap

import requests


GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_MODEL = "openai/gpt-oss-120b"

MAX_PAGE_TEXT_CHARS = 3500
MAX_INTERACTIVE_ELEMENTS = 40
MAX_HISTORY_ITEMS = 6
MAX_PROMPT_CHARS = 25000


def call_groq(
    prompt: str,
    json_mode: bool = False,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from the environment"
        )

    request_body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0,
    }

    if json_mode:
        request_body["response_format"] = {
            "type": "json_object"
        }

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=request_body,
        timeout=90,
    )

    if not response.ok:
        raise RuntimeError(
            "Groq API failed with HTTP "
            f"{response.status_code}: {response.text}"
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            f"Unexpected Groq response format: {data}"
        ) from error


def build_prompt(
    observation: dict,
    task: str,
    history: list,
) -> str:
    page_text = str(
        observation.get("text", "")
    )[:MAX_PAGE_TEXT_CHARS]

    elements = observation.get(
        "interactive_elements",
        [],
    )[:MAX_INTERACTIVE_ELEMENTS]

    recent_history = history[-MAX_HISTORY_ITEMS:]

    # Compact JSON uses fewer characters and tokens than indent=2.
    elements_json = json.dumps(
        elements,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    history_json = json.dumps(
        recent_history,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )

    prompt = textwrap.dedent(
        f"""
        You are an autonomous browser navigation agent.

        USER TASK:
        {task}

        CURRENT PAGE:
        URL: {observation.get("url", "")}
        Title: {observation.get("title", "")}

        VISIBLE PAGE TEXT:
        {page_text}

        VISIBLE INTERACTIVE ELEMENTS:
        {elements_json}

        ACTION HISTORY:
        {history_json}

        RULES:

        1. Use only element IDs present in VISIBLE INTERACTIVE ELEMENTS.
        2. Never invent an element ID, page fact, name, statistic, or URL.
        3. Do not answer from general knowledge.
        4. Do not finish based only on vague homepage content.
        5. Inspect the relevant page before answering.
        6. After each action, inspect the new observation.
        7. Do not repeat failed actions without a clear reason.
        8. Use SCROLL when useful content may be lower on the page.
        9. Use BACK after opening an irrelevant page.
        10. Return exactly one JSON object.

        For team-related tasks:

        - Do not treat testimonials as employees or staff.
        - Look for Team, Our People, Staff, Leadership, Board,
          Who We Are, or About.
        - Open dropdowns using CLICK or HOVER.
        - Only finish after reaching a relevant team or leadership page,
          or confirming that the website does not provide one.

        AVAILABLE ACTIONS:

        CLICK
        {{
          "action": "CLICK",
          "element_id": "12"
        }}

        TYPE
        {{
          "action": "TYPE",
          "element_id": "7",
          "text": "Mumbai"
        }}

        PRESS
        {{
          "action": "PRESS",
          "element_id": "7",
          "key": "Enter"
        }}

        SELECT
        {{
          "action": "SELECT",
          "element_id": "4",
          "value": "Mumbai"
        }}

        HOVER
        {{
          "action": "HOVER",
          "element_id": "9"
        }}

        SCROLL
        {{
          "action": "SCROLL",
          "amount": 900
        }}

        BACK
        {{
          "action": "BACK"
        }}

        WAIT
        {{
          "action": "WAIT",
          "milliseconds": 1500
        }}

        NAVIGATE
        {{
          "action": "NAVIGATE",
          "url": "https://example.com"
        }}

        FINISH
        {{
          "action": "FINISH",
          "answer": "Final answer supported by the website."
        }}
        """
    ).strip()

    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(
            "Prompt is still too large after trimming: "
            f"{len(prompt)} characters"
        )

    return prompt


def send_prompt(prompt: str) -> str:
    return call_groq(
        prompt,
        json_mode=True,
    )


def ask_llm(
    observation: dict,
    task: str,
    history: list,
) -> str:
    prompt = build_prompt(
        observation,
        task,
        history,
    )

    answer = send_prompt(prompt)

    print("Groq action:", answer)

    return answer