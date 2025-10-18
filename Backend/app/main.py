from fastapi import FastAPI
from .routers.routers import r as test_router
from .routers.ml_tickets import router as ticket_router
from fastapi.middleware.cors import CORSMiddleware

from .services.ticket_queue import ticket_queue
from .services.dispatcher import dispatcher

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

@app.on_event("startup")
async def startup_event():
    # запускаем очередь (preload из БД: True)
    await ticket_queue.start(preload_from_db=True)
    # старт Dispatcher
    await dispatcher.start()

@app.on_event("shutdown")
async def shutdown_event():
    await dispatcher.stop()
    await ticket_queue.stop()