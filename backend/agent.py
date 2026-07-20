import asyncio
import json

from browser import Browser
from harness import ActionResult, Harness
from llm import ask_llm


class Agent:
    MAX_STEPS = 20

    def __init__(self):
        self.browser = None
        self.harness = Harness()

    async def observe(self):
        elements = await self.browser.get_interactive_elements()
        page_text = await self.browser.get_text()

        return {
            "url": await self.browser.get_url(),
            "title": await self.browser.get_title(),
            "interactive_elements": elements[:100],
            "text": page_text[:8000],
        }

    async def think(self, observation, task):
        history = self.harness.get_history()

        # requests.post() is synchronous, so run it in a worker thread
        # instead of blocking FastAPI's event loop.
        return await asyncio.to_thread(
            ask_llm,
            observation,
            task,
            history,
        )

    def record(
        self,
        action: str,
        target: str,
        result: str,
    ):
        self.harness.add_action_result(
            ActionResult(
                prev_action=action,
                prev_target=target,
                result=result,
            )
        )

    async def act(self, action):
        action_type = str(
            action.get("action", "")
        ).upper().strip()

        if not action_type:
            raise ValueError(
                "The LLM response did not include an action."
            )

        if action_type == "CLICK":
            element_id = action.get("element_id")

            if element_id is None:
                raise ValueError(
                    "CLICK did not include element_id."
                )

            element_id = str(element_id)
            print("Clicking element:", element_id)

            success = await self.browser.click_by_id(element_id)

            self.record(
                "CLICK",
                element_id,
                "Click succeeded" if success else "Click failed",
            )
            return None

        if action_type == "TYPE":
            element_id = action.get("element_id")
            text = action.get("text")

            if element_id is None:
                raise ValueError(
                    "TYPE did not include element_id."
                )

            if text is None:
                raise ValueError(
                    "TYPE did not include text."
                )

            element_id = str(element_id)
            text = str(text)

            print(
                f'Typing "{text}" into element {element_id}'
            )

            success = await self.browser.fill_by_id(
                element_id,
                text,
            )

            self.record(
                "TYPE",
                element_id,
                (
                    f'Typed "{text}" successfully'
                    if success
                    else f'Failed to type "{text}"'
                ),
            )
            return None

        if action_type == "PRESS":
            element_id = action.get("element_id")
            key = action.get("key")

            if element_id is None:
                raise ValueError(
                    "PRESS did not include element_id."
                )

            if not key:
                raise ValueError(
                    "PRESS did not include key."
                )

            element_id = str(element_id)
            key = str(key)

            success = await self.browser.press_by_id(
                element_id,
                key,
            )

            self.record(
                "PRESS",
                element_id,
                (
                    f'Pressed "{key}" successfully'
                    if success
                    else f'Failed to press "{key}"'
                ),
            )
            return None

        if action_type == "SELECT":
            element_id = action.get("element_id")
            value = action.get("value")

            if element_id is None:
                raise ValueError(
                    "SELECT did not include element_id."
                )

            if value is None:
                raise ValueError(
                    "SELECT did not include value."
                )

            element_id = str(element_id)
            value = str(value)

            success = await self.browser.select_by_id(
                element_id,
                value,
            )

            self.record(
                "SELECT",
                element_id,
                (
                    f'Selected "{value}" successfully'
                    if success
                    else f'Failed to select "{value}"'
                ),
            )
            return None

        if action_type == "HOVER":
            element_id = action.get("element_id")

            if element_id is None:
                raise ValueError(
                    "HOVER did not include element_id."
                )

            element_id = str(element_id)

            success = await self.browser.hover_by_id(
                element_id
            )

            self.record(
                "HOVER",
                element_id,
                "Hover succeeded" if success else "Hover failed",
            )
            return None

        if action_type == "SCROLL":
            amount = action.get("amount", 800)

            try:
                amount = int(amount)
            except (TypeError, ValueError):
                amount = 800

            amount = max(-2000, min(amount, 2000))
            await self.browser.scroll(amount)

            self.record(
                "SCROLL",
                "page",
                f"Scrolled by {amount}px",
            )
            return None

        if action_type == "BACK":
            success = await self.browser.go_back()

            self.record(
                "BACK",
                "browser",
                (
                    "Back navigation succeeded"
                    if success
                    else "Back navigation failed"
                ),
            )
            return None

        if action_type == "WAIT":
            milliseconds = action.get(
                "milliseconds",
                1500,
            )

            try:
                milliseconds = int(milliseconds)
            except (TypeError, ValueError):
                milliseconds = 1500

            milliseconds = max(
                100,
                min(milliseconds, 10000),
            )

            await self.browser.wait(milliseconds)

            self.record(
                "WAIT",
                "page",
                f"Waited {milliseconds} milliseconds",
            )
            return None

        if action_type == "NAVIGATE":
            url = action.get("url")

            if not url:
                raise ValueError(
                    "NAVIGATE did not include a URL."
                )

            url = str(url)
            success = await self.browser.goto(url)

            self.record(
                "NAVIGATE",
                url,
                (
                    "Navigation succeeded"
                    if success
                    else "Navigation failed"
                ),
            )
            return None

        if action_type == "FINISH":
            answer = action.get("answer")

            if not answer:
                raise ValueError(
                    "FINISH did not include an answer."
                )

            answer = str(answer)

            self.record(
                "FINISH",
                "task",
                answer,
            )
            return answer

        raise ValueError(
            f"Unknown action: {action_type}"
        )

    async def run(self, url, task):
        self.browser = Browser()
        self.harness = Harness()

        try:
            await self.browser.start()

            loaded = await self.browser.goto(url)

            if not loaded:
                return "Website did not load."

            for step in range(self.MAX_STEPS):
                print(
                    f"\n--- Agent step {step + 1} "
                    f"of {self.MAX_STEPS} ---"
                )

                observation = await self.observe()

                print("Page:", observation["title"])
                print("URL:", observation["url"])

                response = await self.think(
                    observation,
                    task,
                )

                print("LLM response:", response)

                try:
                    action = json.loads(response)

                except json.JSONDecodeError as error:
                    print(
                        "Invalid JSON returned by LLM:",
                        response,
                    )

                    self.record(
                        "INVALID_JSON",
                        "LLM",
                        str(error),
                    )
                    continue

                if not isinstance(action, dict):
                    self.record(
                        "INVALID_ACTION",
                        "LLM",
                        "Response was not a JSON object.",
                    )
                    continue

                try:
                    result = await self.act(action)

                except Exception as error:
                    print("Action error:", error)

                    self.record(
                        "ACTION_ERROR",
                        str(action.get("action", "unknown")),
                        str(error),
                    )
                    continue

                if result is not None:
                    return result

            return (
                "The agent reached its maximum number "
                "of steps before completing the task."
            )

        finally:
            if self.browser:
                await self.browser.close()