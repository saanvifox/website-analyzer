from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import Agent


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


SCREENSHOT_DIRECTORY = Path("screenshots").resolve()

SCREENSHOT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/screenshots",
    StaticFiles(
        directory=str(SCREENSHOT_DIRECTORY),
    ),
    name="screenshots",
)


class AnalyzeRequest(BaseModel):
    url: str
    task: str


@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {
        "message": "Website Analyzer API is running."
    }


@app.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
) -> dict[str, Any]:
    print(
        "ANALYZE REQUEST STARTED",
        flush=True,
    )

    url = request.url.strip()
    task = request.task.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="A URL is required.",
        )

    if not task:
        raise HTTPException(
            status_code=400,
            detail="A task is required.",
        )

    agent = Agent()

    try:
        result = await agent.run(
            url,
            task,
        )

    except Exception as error:
        print(
            "ANALYZE REQUEST FAILED:",
            error,
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    print(
        "ANALYZE REQUEST FINISHED:",
        str(result.get("answer", ""))[:200],
        flush=True,
    )

    return {
        "url": url,
        **result,
    }