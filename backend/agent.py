from browser import Browser
from llm import ask_llm
import json


class Agent:

    def __init__(self):
        self.browser = None


    def observe(self):

        return {
            "url": self.browser.get_url(),
            "title": self.browser.get_title(),
            "links": self.browser.get_links()[:20],
            "text": self.browser.get_text()[:3000]
        }


    def think(self, observation, task):

        return ask_llm(observation, task)


    def act(self, action):

        action_type = action["action"]

        if action_type == "CLICK":

            target = action["target"]

            print("Clicking:", target)

            self.browser.click_text(target)

            return None


        elif action_type == "SCROLL":

            print("Scrolling")

            self.browser.scroll()

            return None


        elif action_type == "FINISH":

            print("Finished")

            return action["answer"]


        else:

            raise Exception(f"Unknown action: {action_type}")


    def run(self, url, task):

        self.browser = Browser()

        self.browser.goto(url)

        while True:

            observation = self.observe()

            print(observation["title"])

            response = self.think(observation, task)

            print(response)

            action = json.loads(response)

            result = self.act(action)

            if result is not None:

                self.browser.close()

                return result