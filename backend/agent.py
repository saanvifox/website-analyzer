from browser import Browser
from llm import ask_llm
import json


class Agent:

    def __init__(self):
        self.browser = None

    async def observe(self):
        return {
            "url": await self.browser.get_url(),
            "title": await self.browser.get_title(),
            "links": (await self.browser.get_links())[:20],
            "text": (await self.browser.get_text())[:3000],
        }

    def think(self, observation, task):
        return ask_llm(observation, task)

    async def act(self, action):
        action_type = action["action"]

        if action_type == "CLICK":
            target = action["target"]
            print("Clicking:", target)

            await self.browser.click_text(target)
            return None

        if action_type == "SCROLL":
            print("Scrolling")

            await self.browser.scroll()
            return None

        if action_type == "FINISH":
            print("Finished")
            return action["answer"]

        raise ValueError(f"Unknown action: {action_type}")

    async def run(self, url, task):
        self.browser = Browser()

        try:
            await self.browser.start()
            await self.browser.goto(url)

            for _ in range(10):
                observation = await self.observe()

                print(observation["title"])

                response = self.think(observation, task)

                print(response)

                action = json.loads(response)
                result = await self.act(action)

                if result is not None:
                    return result

            return "The agent reached its maximum number of steps."

        finally:
            await self.browser.close()