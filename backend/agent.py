import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

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

        self.steps: list[dict[str, Any]] = []
        self.run_id = ""
        self.screenshot_directory = Path("screenshots")

    def reset_run(self) -> None:
        """
        Reset data for a new website-analysis request.
        """
        self.harness = Harness()
        self.steps = []
        self.run_id = uuid4().hex

        self.screenshot_directory = (
            Path("screenshots") / self.run_id
        )

        self.screenshot_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

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

        This is mainly a fallback because browser actions normally
        return the updated page state.
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

    async def take_step_screenshot(
        self,
        step_number: int,
    ) -> str | None:
        """
        Save a screenshot for one agent step.

        The filename is relative to the Playwright MCP output
        directory configured in mcp_client.py.
        """
        filename = (
            f"{self.run_id}/"
            f"step-{step_number}.png"
        )

        try:
            await self.mcp.call_tool(
                "browser_take_screenshot",
                {
                    "type": "png",

                    # False captures the visible browser viewport.
                    # This is usually clearer and much smaller than
                    # a full-page image.
                    "fullPage": False,

                    "filename": filename,
                },
            )

            expected_file = (
                Path("screenshots")
                / self.run_id
                / f"step-{step_number}.png"
            )

            if not expected_file.exists():
                print(
                    "Screenshot tool completed, but the "
                    "expected file was not found:",
                    expected_file,
                    flush=True,
                )

                return None

            return (
                f"/screenshots/"
                f"{self.run_id}/"
                f"step-{step_number}.png"
            )

        except Exception as error:
            print(
                f"Screenshot failed for step "
                f"{step_number}: {error}",
                flush=True,
            )

            return None

    def add_step(
        self,
        step_number: int,
        action: str,
        arguments: dict[str, Any],
        result: str,
        screenshot_url: str | None,
        status: str = "success",
    ) -> None:
        """
        Store one frontend-displayable agent step.
        """
        self.steps.append(
            {
                "step": step_number,
                "action": action,
                "arguments": arguments,
                "result": result,
                "status": status,
                "screenshot_url": screenshot_url,
            }
        )

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
                "snapshot": updated page state,
                "result": short human-readable action result
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
                "result": "Agent completed the task.",
            }

        result = await self.mcp.call_tool(
            tool_name,
            arguments,
        )

        result_text = self.mcp.result_to_text(
            result
        ).strip()

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
            "result": compact_result,
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
    ) -> dict[str, Any]:
        self.reset_run()

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

            if not current_snapshot:
                current_snapshot = await self.get_snapshot()

            self.record(
                "browser_navigate",
                url,
                "Initial page navigation completed.",
            )

            initial_screenshot = (
                await self.take_step_screenshot(0)
            )

            self.add_step(
                step_number=0,
                action="browser_navigate",
                arguments={"url": url},
                result="Initial page navigation completed.",
                screenshot_url=initial_screenshot,
            )

            for step in range(1, self.MAX_STEPS + 1):
                print(
                    f"\n--- Agent step {step} "
                    f"of {self.MAX_STEPS} ---",
                    flush=True,
                )

                if len(current_snapshot) > 4000:
                    snapshot_for_groq = await self.compress(
                        task,
                        current_snapshot,
                    )
                else:
                    snapshot_for_groq = current_snapshot

                    print(
                        "Skipping compression for small snapshot "
                        f"({len(current_snapshot)} characters).",
                        flush=True,
                    )

                selected = await self.choose_action(
                    task,
                    snapshot_for_groq,
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
                    flush=True,
                )

                try:
                    tool_result = await self.execute_tool(
                        tool_name,
                        arguments,
                    )

                except Exception as error:
                    error_message = f"Tool failed: {error}"

                    print(
                        "Tool error:",
                        error,
                        flush=True,
                    )

                    self.record(
                        tool_name,
                        str(arguments),
                        error_message,
                    )

                    failed_screenshot = (
                        await self.take_step_screenshot(
                            step
                        )
                    )

                    self.add_step(
                        step_number=step,
                        action=tool_name,
                        arguments=arguments,
                        result=error_message,
                        screenshot_url=failed_screenshot,
                        status="error",
                    )

                    # Keep the previous snapshot and allow the LLM
                    # to choose a different action.
                    continue

                answer = tool_result.get("answer")
                action_result = (
                    tool_result.get("result")
                    or f"{tool_name} completed."
                )

                step_screenshot = (
                    await self.take_step_screenshot(
                        step
                    )
                )

                self.add_step(
                    step_number=step,
                    action=tool_name,
                    arguments=arguments,
                    result=action_result,
                    screenshot_url=step_screenshot,
                )

                if answer is not None:
                    return {
                        "answer": answer,
                        "steps": self.steps,
                        "run_id": self.run_id,
                    }

                updated_snapshot = tool_result.get(
                    "snapshot"
                )

                if updated_snapshot:
                    current_snapshot = updated_snapshot
                else:
                    try:
                        current_snapshot = (
                            await self.get_snapshot()
                        )

                    except Exception as error:
                        print(
                            "Snapshot fallback failed:",
                            error,
                            flush=True,
                        )

                        self.record(
                            "browser_snapshot",
                            "",
                            (
                                "Snapshot fallback failed: "
                                f"{error}"
                            ),
                        )

            return {
                "answer": (
                    "The agent reached its maximum "
                    "number of steps."
                ),
                "steps": self.steps,
                "run_id": self.run_id,
            }

        finally:
            await self.mcp.close()