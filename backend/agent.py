import asyncio
from typing import Any

from compressor import compress_snapshot
from harness import ActionResult, Harness
from llm import ask_llm, convert_mcp_tools
from mcp_client import PlaywrightMCPClient


class Agent:
    MAX_STEPS = 20

    def __init__(self):
        self.mcp = PlaywrightMCPClient()
        self.harness = Harness()
        self.groq_tools: list[dict[str, Any]] = []

    def record(
        self,
        action: str,
        target: str,
        result: str,
    ) -> None:
        self.harness.add_action_result(
            ActionResult(
                prev_action=action,
                prev_target=target,
                result=result,
            )
        )

    async def get_snapshot(self) -> str:
        """
        Explicitly request a fresh browser snapshot.

        This should mainly be used as a fallback because Playwright MCP
        normally returns the updated page state after browser actions.
        """
        result = await self.mcp.call_tool(
            "browser_snapshot",
            {},
        )

        snapshot = self.mcp.result_to_text(result).strip()

        if not snapshot:
            raise RuntimeError(
                "Playwright returned an empty snapshot."
            )

        return snapshot

    @staticmethod
    def summarize_tool_result(
        tool_name: str,
        result_text: str,
    ) -> str:
        lowered = result_text.lower()

        if "error" in lowered or "failed" in lowered:
            return result_text[:300]

        return f"{tool_name} completed successfully."

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, str | None]:
        """
        Execute one LLM-selected tool.

        Returns:
            {
                "answer": final answer when finish is called,
                "snapshot": updated MCP page result for browser tools
            }
        """
        if tool_name == "finish":
            answer = arguments.get("answer")

            if not answer:
                raise ValueError(
                    "finish did not include an answer."
                )

            return {
                "answer": str(answer),
                "snapshot": None,
            }

        result = await self.mcp.call_tool(
            tool_name,
            arguments,
        )

        result_text = self.mcp.result_to_text(result).strip()

        compact_result = self.summarize_tool_result(
            tool_name,
            result_text,
        )

        self.record(
            tool_name,
            str(arguments),
            compact_result,
        )

        return {
            "answer": None,
            "snapshot": result_text or None,
        }

    async def compress(
        self,
        task: str,
        snapshot: str,
    ) -> str:
        """
        Run snapshot compression outside the async event loop.
        """
        return await asyncio.to_thread(
            compress_snapshot,
            task,
            snapshot,
        )

    async def choose_action(
        self,
        task: str,
        snapshot: str,
    ) -> dict[str, Any]:
        """
        Run the synchronous Groq request outside the event loop.
        """
        return await asyncio.to_thread(
            ask_llm,
            task,
            snapshot,
            self.harness.get_history(),
            self.groq_tools,
        )

    async def run(
        self,
        url: str,
        task: str,
    ) -> str:
        self.harness = Harness()

        try:
            await self.mcp.start()

            mcp_tools = await self.mcp.list_tools()
            all_tools = convert_mcp_tools(mcp_tools)

            # The initial URL is controlled by the application.
            # The LLM does not need browser_navigate afterward.
            self.groq_tools = [
                tool
                for tool in all_tools
                if tool["function"]["name"]
                != "browser_navigate"
            ]

            navigation_result = await self.mcp.call_tool(
                "browser_navigate",
                {"url": url},
            )

            current_snapshot = (
                self.mcp.result_to_text(
                    navigation_result
                ).strip()
            )

            # Only request a separate snapshot when navigation did not
            # return any usable page state.
            if not current_snapshot:
                current_snapshot = await self.get_snapshot()

            self.record(
                "browser_navigate",
                url,
                "Initial page navigation completed.",
            )

            for step in range(self.MAX_STEPS):
                print(
                    f"\n--- Agent step {step + 1} "
                    f"of {self.MAX_STEPS} ---"
                )

                compressed_snapshot = await self.compress(
                    task,
                    current_snapshot,
                )

                selected = await self.choose_action(
                    task,
                    compressed_snapshot,
                )

                tool_name = selected["name"]
                arguments = selected.get(
                    "arguments",
                    {},
                )

                print(
                    "Groq selected:",
                    tool_name,
                    arguments,
                )

                try:
                    tool_result = await self.execute_tool(
                        tool_name,
                        arguments,
                    )

                except Exception as error:
                    print("Tool error:", error)

                    self.record(
                        tool_name,
                        str(arguments),
                        f"Tool failed: {error}",
                    )

                    # Keep the previous snapshot instead of immediately
                    # making another browser_snapshot call. This avoids
                    # repeated 30-second snapshot timeouts.
                    continue

                answer = tool_result.get("answer")

                if answer is not None:
                    return answer

                updated_snapshot = tool_result.get(
                    "snapshot"
                )

                if updated_snapshot:
                    current_snapshot = updated_snapshot
                else:
                    # Rare fallback for tools that return no page state.
                    try:
                        current_snapshot = (
                            await self.get_snapshot()
                        )
                    except Exception as error:
                        print(
                            "Snapshot fallback failed:",
                            error,
                        )

                        self.record(
                            "browser_snapshot",
                            "",
                            (
                                "Snapshot fallback failed: "
                                f"{error}"
                            ),
                        )

            return (
                "The agent reached its maximum "
                "number of steps."
            )

        finally:
            await self.mcp.close()