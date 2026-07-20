import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


def call_groq(prompt: str, json_mode: bool = False) -> str:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from the environment")

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
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Groq API failed with HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def ask_llm(observation, task, history):

    prompt = f"""
    You are controlling a web browser.

    Your job is to complete this task:

    {task}

    Previous Actions:
    {history}

    Current page:

    URL:
    {observation["url"]}

    Title:
    {observation["title"]}

    Visible navigation items (ONLY these may be clicked):
    {observation["clickable_elements"]}

    Visible page text:
    {observation["text"]}

    IMPORTANT RULES:

    1. You may ONLY click text that appears EXACTLY in the "Visible navigation items" list above.
    2. NEVER invent clickable elements.
    3. NEVER guess.
    4. If the information needed to answer the task is already on the page, return FINISH immediately.
    5. If there is no useful element to click, return FINISH.
    6. The target MUST exactly match the text of one visible item in list above.
    7. Return exactly one JSON object.
    8. Do not include markdown or explanations outside the JSON.
    9. Review the Previous Actions before choosing the next action.
    10. Do not repeat a failed action unless there is a clear reason.
    When returning a FINISH action:

    - Begin with a short, friendly greeting.
    - Example:
    "Okay! I analyzed the website and here's what I found:"

    - Present the answer using clear bullet points.
    - Keep the response concise and easy to read.
    - If appropriate, end with a short concluding sentence.
   
     Valid responses:

    {{
        "action": "CLICK",
        "target": "Research"
    }}

    {{
        "action": "SCROLL"
    }}

    {{
        "action": "FINISH",
        "answer": "Your final answer here."
    }}
    """

    answer = call_groq(prompt, json_mode=True)

    print("Groq action:", answer)

    return answer


def choose_starting_url(task: str):

        prompt = f"""
        You are an expert web navigation assistant.

        Choose the single best starting website for the user's task.

        Rules:
        - Return ONLY one complete HTTPS URL.
        - Do not explain your answer.
        - Do not use markdown.
        - Do not include quotes.
        - Choose an official website whenever possible.
        - For current news, choose a reputable news website.
        - For shopping, choose the relevant official shopping website.
        - If the task mentions a company, prefer that company's official website.

        Examples:

        Task:
        Summarize OpenAI

        https://openai.com

        Task:
        Find today's BBC headlines

        https://www.bbc.com/news

        Task:
        Check Amazon laptop prices

        https://www.amazon.com

        Task:
        Find Apple's newest iPhone

        https://www.apple.com

        Task:
        {task}
        """

        url = call_groq(prompt)

        url = url.strip().strip('"').strip("'")

        if not url.startswith(("http://", "https://")):
            raise RuntimeError(f"Groq returned an invalid URL: {url}")

        print("Chosen URL:", url)

        return url