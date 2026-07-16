import requests

def ask_llm(observation, task):

        prompt = f"""
            You are controlling a web browser.

            Your job is to complete this task:

            {task}

            Current page:

            URL:
            {observation["url"]}

            Title:
            {observation["title"]}

            Visible links (ONLY these may be clicked):
            {observation["links"]}

            Visible page text:
            {observation["text"]}

            IMPORTANT RULES:

            1. You may ONLY click a link that appears EXACTLY in the "Visible links" list above.

            2. NEVER invent links.

            3. NEVER guess.

            4. If the information needed to answer the task is already on the page, return FINISH immediately.

            5. If there is no useful link to click, return FINISH.

            6. The target MUST exactly match the text of one visible link.

            Return ONLY valid JSON.

            Examples:

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
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "kamekichi128/qwen3-4b-instruct-2507",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            }
        )

        data = response.json()
        print(data["message"]["content"])

        return data["message"]["content"]


def choose_starting_url(task: str):

    prompt = f"""
        You are an expert web navigation assistant.

        Your job is to choose the single best starting website for the user's task.

        Rules:
        - Return ONLY one URL.
        - Do not explain your answer.
        - Do not use markdown.
        - Do not include quotes.
        - Choose the official website whenever possible.
        - If the task is about current news, choose a reputable news website.
        - If the task is about shopping, choose the official shopping website.
        - If the task mentions a specific company, use that company's official website.

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

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "kamekichi128/qwen3-4b-instruct-2507",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        }
    )

    data = response.json()

    url = data["message"]["content"].strip()

    print("Chosen URL:", url)

    return url
