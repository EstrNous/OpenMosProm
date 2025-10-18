from fastapi import FastAPI
from Backend.app.api.routers.routers import r as test_router
from Backend.app.api.routers.ml_tickets import router as ticket_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

app.include_router(test_router)
app.include_router(ticket_router)
