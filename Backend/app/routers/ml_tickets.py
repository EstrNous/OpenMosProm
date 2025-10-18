# app/routers/ml_tickets.py
import os
from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pydantic import BaseModel, Field
from ..schemas import EnqueueIn, DequeueOut, ResultIn, EnqueueResponse, DequeueResponse
from ..services.ticket_queue import ticket_queue
from Backend.crud import base_crud
from Backend.db.models import Ticket as TicketModel


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.post(
    "/tickets/enqueue",
    response_model=EnqueueResponse,
    summary="Создать тикет и поставить в очередь",
    description="Техническая ручка для создания тикета в БД и постановки его в очереди. 'В бою' не используется, полезна для тестирования и ручного добавления."
)
async def enqueue_ticket(payload: EnqueueIn = Body(..., examples={
    "existing_dialog": {"summary": "Добавить тикет в существующий диалог", "value": {"dialog_id": 5, "type": "access"}},
    "new_dialog": {"summary": "Создать тикет без dialog_id (создастся новый dialog)", "value": {"dialog_id": None, "type": "other"}}
})):
    ticket_id = await ticket_queue.enqueue_new(dialog_id=payload.dialog_id, type=payload.type)
    return {"ticket_id": ticket_id}


# Удалим, если не потребуется
@router.post(
    "/tickets/dequeue",
    response_model=DequeueResponse,
    summary="Забрать следующий тикет из очереди (Pull)",
    description="Ручка для pull-модели: ML может вызвать эту ручку чтобы получить следующий тикет. В нашей системе с диспетчером это не нужно, но возможность инициативы от ML, таким образом, учтена."
)
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


# Пока заглушки
@router.post(
    "/tickets/result",
    summary="Callback от ML: результат обработки тикета",
    description="""
ML вызывает этот endpoint, чтобы сообщить результат обработки тикета.

*Примеры `result` в теле запроса:*
- Успешный ответ: `{"text":"Сбросили пароль"}`
- Эскалация: `{"reason":"requires-human"}`
- Вызов инструмента: `{"tool_name":"reset_password","parameters":{"user_id":"u123"}}`

По умолчанию, если `solved=true`, тикет будет закрыт.
""",
)
async def ticket_result(payload: ResultIn = Body(..., examples={
    "answer": {"summary": "Успешный ответ", "value": {"ticket_id": 1, "result": {"text": "Пароль сброшен"}, "solved": True}},
    "escalation": {"summary": "Запрос эскалации", "value": {"ticket_id": 2, "result": {"reason": "Requires manual verification"}, "solved": False}},
    "tool_call": {"summary": "Вызов инструмента", "value": {"ticket_id": 3, "result": {"tool_name": "reset_password", "parameters": {"user_id": "user_123"}}, "solved": False}}
})):
    ok = await ticket_queue.get_result(payload.ticket_id, result_payload=payload.result, solved=payload.solved)
    if not ok:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "ok"}
