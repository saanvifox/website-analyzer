import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.1-flash-lite"


def compress_snapshot(task: str, snapshot: str) -> str:
    prompt = f"""
Task:
{task}

Playwright snapshot:
{snapshot}

Compress this snapshot for a browser agent.

Keep:
- Exact element references such as [ref=e12]
- Relevant links, buttons, textboxes, forms, and headings
- Text useful for completing the task
- Useful navigation options
- Errors, alerts, and dialog messages

Remove:
- Repeated content
- Unrelated navigation
- Footer content
- Cookie, privacy, legal, and copyright text
- Decorative or irrelevant content

Do not:
- Change or invent element references
- Choose a browser action
- Answer the task

Return only the compressed snapshot.
""".strip()

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        print(
        f"Snapshot: {len(snapshot)} -> {len(response.text)} characters"
    )


        if response.text:
            return response.text.strip()

    except Exception as error:
        print("Snapshot compression failed:", error)

    return snapshot