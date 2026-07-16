from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from llm import choose_starting_url
from agent import Agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
        "https://website-analyzer-pi.vercel.app/"
    ],
    allow_credentials=True,
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
async def analyze(request: AnalyzeRequest):

    agent = Agent()

    url = request.url

    if url == "":
        url = choose_starting_url(request.task)

    summary = await agent.run(
        url,
        request.task
    )

    return {
        "url": url,
        "summary": summary
    }