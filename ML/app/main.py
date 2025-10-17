from fastapi import FastAPI
from .api.routers import agent

app = FastAPI(title="ML Service API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])