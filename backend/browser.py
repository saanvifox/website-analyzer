from playwright.async_api import (
TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


class Browser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=True,
        )

        self.page = await self.browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000,
            }
        )

    async def goto(self, url: str) -> bool:
        url = url.strip().strip('"').strip("'")

        if not url.startswith(("http://", "https://")):
            print(f"Invalid URL: {url}")
            return False

        try:
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            await self.wait_after_action()
            return True

        except Exception as error:
            print("Navigation warning:", error)
            return False

    async def get_title(self) -> str:
        return await self.page.title()

    async def get_text(self) -> str:
        try:
            text = await self.page.locator(
                "body"
            ).inner_text(timeout=10000)

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            unique_lines = list(dict.fromkeys(lines))

            return "\n".join(unique_lines)

        except Exception:
            return ""

    async def get_url(self) -> str:
        return self.page.url

    async def wait_after_action(self):
        try:
            await self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )

        except PlaywrightTimeoutError:
            pass

        await self.page.wait_for_timeout(750)

    async def get_interactive_elements(self):
        """
        Finds visible, useful interactive elements and assigns temporary IDs.

        The IDs remain valid until the next observation refresh.
        """

        return await self.page.evaluate(
            """
            () => {
                document
                    .querySelectorAll("[data-agent-id]")
                    .forEach(element => {
                        element.removeAttribute("data-agent-id");
                    });

                const selector = [
                    "a",
                    "button",
                    "input",
                    "textarea",
                    "select",
                    "[role='button']",
                    "[role='link']",
                    "[role='menuitem']",
                    "[role='combobox']"
                ].join(",");

                const elements = Array.from(
                    document.querySelectorAll(selector)
                );

                const results = [];
                let id = 0;

                for (const element of elements) {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();

                    const visible =
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        Number(style.opacity || 1) > 0 &&
                        rect.width > 0 &&
                        rect.height > 0;

                    if (!visible || element.disabled) {
                        continue;
                    }

                    const tag = element.tagName.toLowerCase();
                    const type = (
                        element.getAttribute("type") || ""
                    ).toLowerCase();

                    if (tag === "input" && type === "hidden") {
                        continue;
                    }

                    const text = (
                        element.innerText ||
                        element.value ||
                        element.getAttribute("aria-label") ||
                        element.getAttribute("title") ||
                        element.getAttribute("alt") ||
                        ""
                    )
                        .trim()
                        .replace(/\\s+/g, " ")
                        .slice(0, 120);

                    const placeholder = (
                        element.getAttribute("placeholder") || ""
                    )
                        .trim()
                        .slice(0, 120);

                    const hasUsefulDescription =
                        Boolean(text) ||
                        Boolean(placeholder) ||
                        Boolean(element.getAttribute("aria-label")) ||
                        tag === "select";

                    if (!hasUsefulDescription) {
                        continue;
                    }

                    const elementId = String(id);

                    element.setAttribute(
                        "data-agent-id",
                        elementId
                    );

                    const result = {
                        id: elementId,
                        tag
                    };

                    if (text) {
                        result.text = text;
                    }

                    if (placeholder) {
                        result.placeholder = placeholder;
                    }

                    if (type) {
                        result.type = type;
                    }

                    if (tag === "select") {
                        result.options = Array.from(
                            element.options
                        )
                            .map(option => ({
                                label: option.text.trim(),
                                value: option.value
                            }))
                            .slice(0, 20);
                    }

                    results.push(result);
                    id += 1;
                }

                return results;
            }
            """
        )

    def locator_by_id(self, element_id: str):
        return self.page.locator(
            f'[data-agent-id="{element_id}"]'
        )

    async def click_by_id(self, element_id: str) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(
                    f"Element ID {element_id} was not found."
                )
                return False

            target = locator.first

            await target.scroll_into_view_if_needed()

            try:
                await target.click(timeout=10000)

            except Exception:
                print(
                    f"Normal click failed for element "
                    f"{element_id}; trying JavaScript click."
                )

                await target.evaluate(
                    "element => element.click()"
                )

            await self.wait_after_action()
            return True

        except Exception as error:
            print(
                f"Click failed for element "
                f"{element_id}: {error}"
            )
            return False

    async def hover_by_id(self, element_id: str) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(
                    f"Element ID {element_id} was not found."
                )
                return False

            target = locator.first

            await target.scroll_into_view_if_needed()
            await target.hover(timeout=10000)
            await self.page.wait_for_timeout(1000)

            return True

        except Exception as error:
            print(
                f"Hover failed for element "
                f"{element_id}: {error}"
            )
            return False

    async def fill_by_id(
        self,
        element_id: str,
        text: str,
    ) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(
                    f"Input ID {element_id} was not found."
                )
                return False

            target = locator.first

            await target.scroll_into_view_if_needed()
            await target.click(timeout=10000)

            tag_name = await target.evaluate(
                "element => element.tagName.toLowerCase()"
            )

            is_contenteditable = await target.evaluate(
                """
                element =>
                    element.getAttribute("contenteditable") === "true"
                """
            )

            if tag_name in ("input", "textarea"):
                try:
                    await target.fill(text)

                except Exception:
                    await target.press("Control+A")
                    await target.type(
                        text,
                        delay=30,
                    )

            elif is_contenteditable:
                try:
                    await target.fill(text)

                except Exception:
                    await target.press("Control+A")
                    await target.type(
                        text,
                        delay=30,
                    )

            else:
                print(
                    f"Element {element_id} is not editable."
                )
                return False

            await self.page.wait_for_timeout(500)
            return True

        except Exception as error:
            print(
                f"Typing failed for element "
                f"{element_id}: {error}"
            )
            return False

    async def press_by_id(
        self,
        element_id: str,
        key: str,
    ) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(
                    f"Element ID {element_id} was not found."
                )
                return False

            await locator.first.press(key)
            await self.wait_after_action()

            return True

        except Exception as error:
            print(
                f'Key press "{key}" failed on element '
                f"{element_id}: {error}"
            )
            return False

    async def select_by_id(
        self,
        element_id: str,
        value: str,
    ) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(
                    f"Select ID {element_id} was not found."
                )
                return False

            target = locator.first

            try:
                await target.select_option(label=value)

            except Exception:
                await target.select_option(value=value)

            await self.wait_after_action()
            return True

        except Exception as error:
            print(
                f'Select failed for element {element_id}, '
                f'value "{value}": {error}'
            )
            return False

    async def scroll(self, amount: int = 800):
        amount = max(
            -2000,
            min(amount, 2000),
        )

        await self.page.mouse.wheel(
            0,
            amount,
        )

        await self.page.wait_for_timeout(750)

    async def go_back(self) -> bool:
        try:
            response = await self.page.go_back(
                wait_until="domcontentloaded",
                timeout=15000,
            )

            if response is None:
                print(
                    "No previous page in browser history."
                )
                return False

            await self.wait_after_action()
            return True

        except Exception as error:
            print(
                "Back navigation failed:",
                error,
            )
            return False

    async def wait(
        self,
        milliseconds: int = 1500,
    ):
        milliseconds = max(
            100,
            min(milliseconds, 10000),
        )

        await self.page.wait_for_timeout(
            milliseconds
        )

    async def screenshot(
        self,
        filename: str = "page.png",
    ):
        await self.page.screenshot(
            path=filename,
            full_page=True,
        )

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()

        finally:
            if self.playwright:
                await self.playwright.stop()