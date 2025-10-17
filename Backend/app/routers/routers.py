# app/routers/routers.py
import os
import time

import httpx
from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv
from ..schemas import PromptRequest, SimpleAnswer, SupportRequest
from ..services import simulation_manager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Backend.crud import base_crud
from ..services.ticket_queue import ticket_queue

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# Загружаем переменные окружения
load_dotenv()

r = APIRouter()

ML_API_URL = os.getenv('ML_API_URL')

@r.post("/test-ml", response_model=SimpleAnswer)
async def test_func(request: PromptRequest):
    ml_request = {
        "prompt": request.prompt
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_API_URL}/api/v1/agent/test-prompt",
                json=ml_request,
                timeout=90.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ml service is unavailable: {e}"
        )

@r.post("/api/new_ticket")
async def create_ticket_endpoint(dialog_id: int | None = None, type: str | None = None):
    """
    Создать тикет в БД. Возвращает JSON с ticket_id и полями.
    """
    db = SessionLocal()
    try:
        # если нужен диалог и его нет — создаём
        dialog = None
        if dialog_id is None:
            dialog = base_crud.create_dialog(db, session_id=f"sim-{int(os.getpid())}-{int(time.time())}")
            dialog_id = dialog.id
        else:
            dialog = base_crud.get_dialog(db, dialog_id)

        ticket = base_crud.create_ticket(db, dialog_id=dialog_id, type=type)

        await ticket_queue.enqueue_existing(ticket.id)

        return {
            "ticket_id": ticket.id,
            "dialog_id": ticket.dialog_id,
            "status": ticket.status,
            "created_at": str(ticket.created_at)
        }
    finally:
        db.close()

# Получение запроса от "пользователя"
@r.post("/support/process", response_model=SupportRequest)
async def process_support_request(request: SupportRequest):
    """
    Обработка входящего обращения.
    """
    print(f"[support/process] Получено обращение от {request.user_id}: {request.user_message[:200]}...")

    db = SessionLocal()
    try:
        # 1) Создаём диалог
        dialog = base_crud.create_dialog(db, session_id=f"{request.user_id}-{request.timestamp}")
        # 2) Создаём сообщение
        base_crud.create_message(db, dialog_id=dialog.id, content=request.user_message)
        # 3) Создаём тикет в БД
        ticket = base_crud.create_ticket(db, dialog_id=dialog.id, type=None)
        ticket_id = ticket.id
    except Exception as e:
        print(f"[support/process] Ошибка при создании тикета: {e}")
        raise HTTPException(status_code=500, detail="error creating ticket")
    finally:
        db.close()

    try:
        await ticket_queue.enqueue_existing(ticket_id)
    except Exception as e:
        # очередь недоступна — всё ещё вернём 201 (тикет в БД есть), но логируем ошибку
        print(f"[support/process] Не удалось положить ticket {ticket_id} в очередь: {e}")

    return request

@r.post("/simulate/start")
async def simulate_start():
    started = await simulation_manager.start_simulation()
    if not started:
        return {"status": "already_running"}
    return {"status": "started"}

@r.post("/simulate/stop")
async def simulate_stop():
    await simulation_manager.stop_simulation()
    return {"status": "stopped"}

@r.get("/simulate/status")
async def simulate_status():
    return simulation_manager.status()
