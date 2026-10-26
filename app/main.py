
from fastapi import FastAPI

app = FastAPI(
    title="SI ORBIT",
    description="An evidence-driven agent for investigating web UI bugs.",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "project": "SI ORBIT",
        "status": "running",
        "message": "Don't just detect the bug. Investigate the evidence.",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
