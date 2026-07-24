from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
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

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"message": "Hello World"}



@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
   

    url = request.url.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="A URL is required.",
        )
    agent = Agent()

    summary = await agent.run(  
        url,  
        request.task, 
          )

    return {
        "url": url,
        "summary": summary,
    }