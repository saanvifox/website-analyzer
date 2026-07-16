from browser import Browser
from llm import ask_llm
import json


class Agent:

    def __init__(self):
        self.browser = None


    async def observe(self):

        observation = {
            "url": await self.browser.get_url(),
            "title": await self.browser.get_title(),
            "links": (await self.browser.get_links())[:20],
            "text": (await self.browser.get_text())[:3000]
        }

        return observation


    def think(self, observation, task):

        # ask_llm() is synchronous because it uses requests.post()
        return ask_llm(observation, task)


    async def act(self, action):

        action_type = action["action"]

        if action_type == "CLICK":

            target = action["target"]

            print(f"Clicking: {target}")

            await self.browser.click_text(target)

            return None


        elif action_type == "SCROLL":

            print("Scrolling")

            await self.browser.scroll()

            return None


        elif action_type == "FINISH":

            print("Task Complete")

            return action["answer"]


        else:

            raise Exception(f"Unknown action: {action_type}")


    async def run(self, url, task):

        self.browser = Browser()

        await self.browser.start()

        await self.browser.goto(url)

        while True:

            observation = await self.observe()

            print(observation["title"])

            response = self.think(
                observation,
                task
            )

            print(response)

            action = json.loads(response)

            result = await self.act(action)

            if result is not None:

                await self.browser.close()

                return result