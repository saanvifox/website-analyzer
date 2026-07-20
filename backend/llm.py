import json
import os

import requests


GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)
GROQ_MODEL = "openai/gpt-oss-120b"


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
        return (
            data["choices"][0]["message"]["content"]
            .strip()
        )
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            f"Unexpected Groq response: {data}"
        ) from error


def ask_llm(observation, task, history):
    elements_json = json.dumps(
        observation["interactive_elements"],
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
You are an autonomous browser navigation agent.

USER TASK:
{task}

CURRENT PAGE:
URL: {observation["url"]}
Title: {observation["title"]}

VISIBLE PAGE TEXT:
{observation["text"]}

VISIBLE INTERACTIVE ELEMENTS:
{elements_json}

ACTION HISTORY:
{history}

Your job is to complete the task by navigating and interacting with
the current website.
Feel free to search things with text you find appropriate. Sometimes you have
to click on the searched item to confirm your search. Feel free to pick the top
result when asked for "best" item.

RULES:

1. Use only element IDs present in VISIBLE INTERACTIVE ELEMENTS.
2. Never invent an element ID, page fact, name, statistic, or URL.
3. Do not answer from general knowledge when the task asks you to
   inspect the website.
4. Do not return FINISH based on vague or partial homepage text.
5. Before FINISH, reach the page, result, profile, table, map, or
   detail view that directly supports the answer.
6. After every click, hover, search, selection, or navigation, inspect
   the next observation before deciding what to do.
7. Do not repeat a failed action unless the page changed and there is
   a clear reason to retry it.
8. Use SCROLL when relevant controls or content may be farther down.
9. Use BACK when you opened an irrelevant page.
10. Use WAIT only when dynamic content is probably still loading.
11. Use NAVIGATE only with a complete HTTP or HTTPS URL that is
    clearly relevant to the task.
12. Return exactly one JSON object with no markdown or extra text.

TASK-SPECIFIC GUIDANCE:

- For employees, staff, founders, leadership, or team members, look
  for People, Our People, Team, Staff, Leadership, About, Who We Are,
  or similar navigation. Open menus with CLICK or HOVER as needed.

- For a city, location, product, article, map value, weather value,
  or other specific item, look for an input, search field, combobox,
  filter, or location selector. TYPE the requested value, then PRESS
  Enter or click the matching result. Read the updated content before
  finishing.

- For native select menus, use SELECT with one of the option labels or
  values shown in the element's options list.

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
  "url": "https://example.com/relevant-page"
}}

FINISH
{{
  "action": "FINISH",
  "answer": "Final answer supported by the website."
}}

FINISH only when there is enough website evidence to answer. If the
site does not provide the requested information, say that clearly
instead of guessing.
"""

    answer = call_groq(
        prompt,
        json_mode=True,
    )

    print("Groq action:", answer)
    return answer


def choose_starting_url(task: str):
    prompt = f"""
You are choosing a starting website for a browser agent.

TASK:
{task}

Return exactly one complete HTTPS URL.

Rules:
- Return only the URL.
- Do not include quotes.
- Do not include markdown.
- Prefer the official website when a specific organization is named.
- Prefer a reputable source when current news is requested.
- Do not invent a domain.
"""

    url = call_groq(prompt)

    url = url.strip().strip('"').strip("'")

    if not url.startswith(("http://", "https://")):
        raise RuntimeError(
            f"Groq returned an invalid URL: {url}"
        )

    print("Chosen URL:", url)
    return url