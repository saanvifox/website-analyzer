from browser import Browser
from llm import ask_llm
from harness import Harness, ActionResult
import json


class Agent:

    def __init__(self):
        self.browser = None
        self.harness = Harness()

    async def observe(self):
        return {
            "url": await self.browser.get_url(),
            "title": await self.browser.get_title(),
            "clickable_elements": (
                await self.browser.get_clickable_elements()
            )[:20],
            "text": (await self.browser.get_text())[:3000],
        }

    def think(self, observation, task):
        history = self.harness.get_history()
        return ask_llm(observation, task, history)

    async def act(self, action):
        action_type = action.get("action", "").upper()

        if not action_type:
            raise ValueError("The LLM response did not include an action.")

        if action_type == "CLICK":
            target = action.get("target")

            if not target:
                raise ValueError("The CLICK action did not include a target.")

            print("Clicking:", target)

            success = await self.browser.click_text(target)

            self.harness.add_action_result(
                ActionResult(
                    prev_action="CLICK",
                    prev_target=target,
                    result="Click succeeded" if success else "Click failed"
                )
            )

            return None

        if action_type == "SCROLL":
            print("Scrolling")

            try:
                await self.browser.scroll()

                self.harness.add_action_result(
                    ActionResult(
                        prev_action="SCROLL",
                        prev_target="page",
                        result="Scroll succeeded"
                    )
                )

            except Exception as error:
                self.harness.add_action_result(
                    ActionResult(
                        prev_action="SCROLL",
                        prev_target="page",
                        result=f"Scroll failed: {error}"
                    )
                )

            return None

        if action_type == "FINISH":
            print("Finished")

            answer = action.get("answer")

            if not answer:
                raise ValueError("The FINISH action did not include an answer.")

            self.harness.add_action_result(
                ActionResult(
                    prev_action="FINISH",
                    prev_target="task",
                    result=answer
                )
            )

            return answer

        raise ValueError(f"Unknown action: {action_type}")

    async def run(self, url, task):
        self.browser = Browser()
        self.harness = Harness()

        try:
            await self.browser.start()

            loaded = await self.browser.goto(url)

            if not loaded:
                return "Website did not load."

            for _ in range(10):
                observation = await self.observe()

                print(observation["title"])

                response = self.think(observation, task)

                print(response)

                try:
                    action = json.loads(response)

                except json.JSONDecodeError as error:
                    print("Invalid JSON returned by LLM:", response)
                    return f"Invalid JSON: {error}"

                if not isinstance(action, dict):
                    return (
                        "The LLM returned JSON, but it was not a JSON object."
                    )

                result = await self.act(action)

                if result is not None:
                    return result

            return "The agent reached its maximum number of steps."

        finally:
            await self.browser.close()