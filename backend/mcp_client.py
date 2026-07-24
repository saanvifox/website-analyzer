from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PlaywrightMCPClient:
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()

    async def start(self) -> None:
        screenshot_output_directory = (
            Path("screenshots").resolve()
        )

        screenshot_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        server_params = StdioServerParameters(
            command="npx",
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
                "--output-dir",
                str(screenshot_output_directory),
            ],
        )

        read_stream, write_stream = (
            await self.exit_stack.enter_async_context(
                stdio_client(server_params)
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

    async def list_tools(self) -> list[Any]:
        if self.session is None:
            raise RuntimeError(
                "Playwright MCP is not running."
            )

        result = await self.session.list_tools()

        return result.tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        if self.session is None:
            raise RuntimeError(
                "Playwright MCP is not running."
            )

        result = await self.session.call_tool(
            name,
            arguments=arguments or {},
        )

        if getattr(result, "isError", False):
            error_text = self.result_to_text(result)

            raise RuntimeError(
                error_text
                or f"Playwright MCP tool failed: {name}"
            )

        return result

    @staticmethod
    def result_to_text(
        result: Any,
    ) -> str:
        parts: list[str] = []

        for item in getattr(
            result,
            "content",
            [],
        ):
            text = getattr(
                item,
                "text",
                None,
            )

            if text:
                parts.append(text)

        structured = getattr(
            result,
            "structuredContent",
            None,
        )

        if structured:
            parts.append(
                str(structured)
            )

        return "\n".join(
            parts
        ).strip()

    async def close(self) -> None:
        await self.exit_stack.aclose()

        self.session = None

        # Create a new stack so the same client object
        # can be started again after being closed.
        self.exit_stack = AsyncExitStack()