from pathlib import Path

from mcp import StdioServerParameters


def create_mcp_server_params() -> StdioServerParameters:
    screenshot_output_directory = Path(
        "/app/screenshots"
    )

    screenshot_output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return StdioServerParameters(
        command="playwright-mcp",
        args=[
            "--headless",
            "--isolated",
            "--browser",
            "chrome",
            "--snapshot-mode",
            "full",
            "--codegen",
            "none",
            "--image-responses",
            "omit",
            "--output-dir",
            "/app/screenshots"
        ],
    )