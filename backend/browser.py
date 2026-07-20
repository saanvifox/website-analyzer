from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class Browser:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=True
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

    async def get_title(self):
        return await self.page.title()

    async def get_text(self):
        try:
            return await self.page.locator("body").inner_text(
                timeout=10000
            )
        except Exception:
            return ""

    async def get_url(self):
        return self.page.url

    async def wait_after_action(self):
        try:
            await self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )
        except PlaywrightTimeoutError:
            pass

        try:
            await self.page.wait_for_timeout(1000)
        except Exception:
            pass

    async def get_interactive_elements(self):
        """
        Finds visible interactive elements and assigns each one a temporary
        data-agent-id. The LLM interacts using these IDs instead of text.
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
                    "option",
                    "[role='button']",
                    "[role='link']",
                    "[role='menuitem']",
                    "[role='option']",
                    "[role='tab']",
                    "[role='checkbox']",
                    "[role='radio']",
                    "[role='combobox']",
                    "[contenteditable='true']",
                    "[onclick]",
                    "[tabindex]"
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

                    if (!visible) {
                        continue;
                    }

                    if (element.disabled) {
                        continue;
                    }

                    if (
                        element.tagName.toLowerCase() === "input" &&
                        element.type === "hidden"
                    ) {
                        continue;
                    }

                    const elementId = String(id);
                    element.setAttribute("data-agent-id", elementId);

                    const tag = element.tagName.toLowerCase();
                    const role =
                        element.getAttribute("role") ||
                        tag;

                    const text = (
                        element.innerText ||
                        element.value ||
                        element.getAttribute("aria-label") ||
                        element.getAttribute("title") ||
                        element.getAttribute("alt") ||
                        ""
                    ).trim().replace(/\\s+/g, " ").slice(0, 200);

                    const placeholder =
                        element.getAttribute("placeholder") || "";

                    const name =
                        element.getAttribute("name") || "";

                    const type =
                        element.getAttribute("type") || "";

                    const href =
                        element.getAttribute("href") || "";

                    results.push({
                        id: elementId,
                        tag,
                        role,
                        text,
                        placeholder,
                        name,
                        type,
                        href: href.slice(0, 300)
                    });

                    id += 1;
                }

                return results;
            }
            """
        )

    def locator_by_id(self, element_id):
        return self.page.locator(
            f'[data-agent-id="{element_id}"]'
        )

    async def click_by_id(self, element_id: str) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(f"Element ID {element_id} was not found.")
                return False

            await locator.first.scroll_into_view_if_needed()
            await locator.first.click(timeout=10000)

            await self.wait_after_action()
            return True

        except Exception as error:
            print(f"Click failed for element {element_id}: {error}")
            return False

    async def hover_by_id(self, element_id: str) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                return False

            await locator.first.scroll_into_view_if_needed()
            await locator.first.hover(timeout=10000)

            await self.page.wait_for_timeout(750)
            return True

        except Exception as error:
            print(f"Hover failed for element {element_id}: {error}")
            return False

    async def fill_by_id(
        self,
        element_id: str,
        text: str,
    ) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
                print(f"Input ID {element_id} was not found.")
                return False

            await locator.first.scroll_into_view_if_needed()
            await locator.first.click(timeout=10000)

            tag_name = await locator.first.evaluate(
                "element => element.tagName.toLowerCase()"
            )

            is_contenteditable = await locator.first.evaluate(
                """
                element =>
                    element.getAttribute("contenteditable") === "true"
                """
            )

            if tag_name in ("input", "textarea"):
                await locator.first.fill(text)
            elif is_contenteditable:
                await locator.first.fill(text)
            else:
                print(
                    f"Element {element_id} is not an editable field."
                )
                return False

            await self.page.wait_for_timeout(500)
            return True

        except Exception as error:
            print(f"Typing failed for element {element_id}: {error}")
            return False

    async def press_by_id(
        self,
        element_id: str,
        key: str,
    ) -> bool:
        try:
            locator = self.locator_by_id(element_id)

            if await locator.count() == 0:
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
                return False

            try:
                await locator.first.select_option(label=value)
            except Exception:
                await locator.first.select_option(value=value)

            await self.wait_after_action()
            return True

        except Exception as error:
            print(
                f'Select failed for element {element_id}, '
                f'value "{value}": {error}'
            )
            return False

    async def scroll(self, amount: int = 800):
        await self.page.mouse.wheel(0, amount)
        await self.page.wait_for_timeout(750)

    async def go_back(self) -> bool:
        try:
            await self.page.go_back(
                wait_until="domcontentloaded",
                timeout=15000,
            )

            await self.wait_after_action()
            return True

        except Exception as error:
            print("Back navigation failed:", error)
            return False

    async def wait(self, milliseconds: int = 1500):
        milliseconds = max(100, min(milliseconds, 10000))
        await self.page.wait_for_timeout(milliseconds)

    async def screenshot(self, filename="page.png"):
        await self.page.screenshot(
            path=filename,
            full_page=True,
        )

    async def close(self):
        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()