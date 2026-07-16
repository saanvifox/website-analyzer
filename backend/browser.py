from playwright.sync_api import sync_playwright


class Browser:

    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()


    def goto(self, url: str):
        self.page.goto(url)


    def get_title(self):
        return self.page.title()


    def get_text(self):
        return self.page.locator("body").inner_text()


    def click(self, selector: str):
        self.page.click(selector)


    def click_text(self, text: str):
       self.page.locator(f'a:has-text("{text}")').first.click()


    def type(self, selector: str, text: str):
        self.page.fill(selector, text)


    def scroll(self):
        self.page.mouse.wheel(0, 1000)


    def get_url(self):
        return self.page.url


    def get_links(self):
        return self.page.locator("a").evaluate_all(
            """
            elements => elements.map(e => ({
                text: e.innerText,
                href: e.href
            }))
            """
        )


    def screenshot(self, filename="page.png"):
        self.page.screenshot(path=filename)


    def close(self):
        self.browser.close()
        self.playwright.stop()