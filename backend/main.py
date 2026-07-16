from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from llm import choose_starting_url
from agent import Agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str
    task: str


@app.get("/")
def home():
    return {"message": "Hello World"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    agent = Agent()

    url = request.url.strip()

    if not url:
        url = choose_starting_url(request.task)

    summary = agent.run(
        url,
        request.task
    )

    return {
        "url": url,
        "summary": summary
    }