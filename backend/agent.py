import asyncio

from harness import ActionResult, Harness
from llm import ask_llm, convert_mcp_tools
from mcp_client import PlaywrightMCPClient
from compressor import compress_snapshot


class Agent:
    MAX_STEPS = 20

    def __init__(self):
        self.mcp = PlaywrightMCPClient()
        self.harness = Harness()
        self.groq_tools = []

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

    async def get_snapshot(self) -> str:
        result = await self.mcp.call_tool(
            "browser_snapshot",
            {},
        )

        snapshot = self.mcp.result_to_text(result)

        if not snapshot:
            raise RuntimeError(
                "Playwright returned an empty snapshot."
            )

        return snapshot

    async def execute_tool( self, tool_name: str, arguments: dict):
        if tool_name == "finish":
            answer = arguments.get("answer")

            if not answer:
                raise ValueError(
                    "finish did not include an answer."
                )

            return str(answer)

        result = await self.mcp.call_tool(
            tool_name,
            arguments,
        )

        result_text = self.mcp.result_to_text(result)

        compact_result = (
            self.summarize_tool_result(
                tool_name,
                result_text,
            )
        )

        self.record(
            tool_name,
            str(arguments),
            compact_result,
        )

        return None
    
    @staticmethod
    def summarize_tool_result(
        tool_name: str,
        result_text: str,
    ) -> str:
        lowered = result_text.lower()

        if "error" in lowered or "failed" in lowered:
            return result_text[:300]

        return f"{tool_name} completed successfully."
    
    async def run(self, url, task):
        self.harness = Harness()

        try:
            await self.mcp.start()

            mcp_tools = await self.mcp.list_tools()
            all_tools = convert_mcp_tools(mcp_tools)

        

            self.groq_tools = [
                tool
                for tool in all_tools
                if tool["function"]["name"] != "browser_navigate"
            ]

            navigation = await self.mcp.call_tool(
                "browser_navigate",
                {"url": url},
            )

            self.record(
                "browser_navigate",
                url,
                self.mcp.result_to_text(
                    navigation
                )[:1500],
            )

            for step in range(self.MAX_STEPS):
                print(
                    f"\n--- Agent step {step + 1} "
                    f"of {self.MAX_STEPS} ---"
                )

                # Fresh snapshot means fresh DOM refs.
                snapshot = await self.get_snapshot()

                snapshot = await asyncio.to_thread(
                                            compress_snapshot,
                                            task,
                                            snapshot,
                                        )


                selected = await asyncio.to_thread(
                    ask_llm,
                    task,
                    snapshot,
                    self.harness.get_history(),
                    self.groq_tools,
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
                    answer = await self.execute_tool(
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

                    continue

                if answer is not None:
                    return answer

            return (
                "The agent reached its maximum "
                "number of steps."
            )

        finally:
            await self.mcp.close()