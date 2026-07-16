from playwright.async_api import async_playwright


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

        self.page = await self.browser.new_page()

    async def goto(self, url: str):
        try:
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as error:
            print("Navigation warning:", error)

    async def get_title(self):
        return await self.page.title()

    async def get_text(self):
        return await self.page.locator("body").inner_text()

    async def click(self, selector: str):
        await self.page.click(selector)

    async def click_text(self, text: str):
        await self.page.locator(
            f'a:has-text("{text}")'
        ).first.click(timeout=10000)

    async def type(self, selector: str, text: str):
        await self.page.fill(selector, text)

    async def scroll(self):
        await self.page.mouse.wheel(0, 1000)

    async def get_url(self):
        return self.page.url

    async def get_links(self):
        return await self.page.locator("a").evaluate_all(
            """
            elements => elements.map(e => ({
                text: e.innerText,
                href: e.href
            }))
            """
        )

    async def screenshot(self, filename="page.png"):
        await self.page.screenshot(path=filename)

    async def close(self):
        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()