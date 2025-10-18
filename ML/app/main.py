from contextlib import asynccontextmanager

from fastapi import FastAPI
from .api.routers import agent
from .core.settings import setup_services, shutdown_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_services()
    yield
    await shutdown_services()


app = FastAPI(title="ML Service API", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
