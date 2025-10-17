# app/routers/ml_tickets.py
import os
from fastapi import APIRouter, HTTPException, status
from typing import Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from ..schemas import EnqueueIn, DequeueOut, ResultIn
from ..services.ticket_queue import ticket_queue
from Backend.crud import base_crud
from Backend.db.models import Ticket as TicketModel


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


router = APIRouter(prefix="/api/ml", tags=["ml-tickets"])

# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/tickets/enqueue")
async def enqueue_ticket(payload: EnqueueIn):
    ticket_id = await ticket_queue.enqueue_new(dialog_id=payload.dialog_id, type=payload.type)
    return {"ticket_id": ticket_id}

@router.post("/tickets/dequeue", response_model=DequeueOut)
async def dequeue_ticket(worker_id: Optional[str] = None):
    ticket_id = await ticket_queue.dequeue(worker_id=worker_id, wait=True, timeout=1.0)
    if ticket_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tickets available")
    db = SessionLocal()
    try:
        t = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
        if not t:
            return {"ticket_id": ticket_id, "dialog_id": None, "status": "in_progress"}
        return {"ticket_id": t.id, "dialog_id": t.dialog_id, "status": t.status}
    finally:
        db.close()

@router.post("/tickets/result")
async def ticket_result(payload: ResultIn):
    ok = await ticket_queue.get_result(payload.ticket_id, result_payload=payload.result, solved=payload.solved)
    if not ok:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "ok"}