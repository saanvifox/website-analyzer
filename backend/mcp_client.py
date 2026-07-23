from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PlaywrightMCPClient:
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()

    async def start(self):
        server = StdioServerParameters(
            command="npx.cmd",
            args=[
                "@playwright/mcp@latest",
                "--headless",
                "--isolated",
                "--snapshot-mode",
                "full",
                "--codegen",
                "none",
                "--image-responses",
                "omit",
            ],
        )

        read_stream, write_stream = (
            await self.exit_stack.enter_async_context(
                stdio_client(server)
            )
        )

        self.session = (
            await self.exit_stack.enter_async_context(
                ClientSession(
                    read_stream,
                    write_stream,
                )
            )
        )

        await self.session.initialize()

    async def list_tools(self):
        if self.session is None:
            raise RuntimeError(
                "Playwright MCP is not running."
            )

        result = await self.session.list_tools()
        return result.tools

    async def call_tool(
        self,
        name: str,
        arguments: dict | None = None,
    ):
        if self.session is None:
            raise RuntimeError(
                "Playwright MCP is not running."
            )

        result = await self.session.call_tool(
            name,
            arguments=arguments or {},
        )

        if getattr(result, "isError", False):
            raise RuntimeError(
                self.result_to_text(result)
            )

        return result

    @staticmethod
    def result_to_text(result) -> str:
        parts = []

        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)

            if text:
                parts.append(text)

        structured = getattr(
            result,
            "structuredContent",
            None,
        )

        if structured:
            parts.append(str(structured))

        return "\n".join(parts).strip()

    async def close(self):
        await self.exit_stack.aclose()
        self.session = None