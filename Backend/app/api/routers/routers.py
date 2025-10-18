import os
import httpx

from fastapi import APIRouter, HTTPException, status, Body
from dotenv import load_dotenv
from Backend.app.schemas import PromptRequest, SimpleAnswer, SupportRequest, SupportResponse
from Backend.app.services import simulation_manager
from Backend.app.services.ticket_queue import ticket_queue
from Backend.crud import base_crud
from Backend.crud.base_crud import get_ticket_times, get_tickets_by_status
from Backend.db.session import get_db

# Загружаем переменные окружения
load_dotenv()

r = APIRouter(tags=["Support"])

db = get_db()
ML_API_URL = os.getenv('ML_API_URL')


@r.post("/test-ml", response_model=SimpleAnswer, summary="Тестовый запрос к ML", description="Отправляет prompt в ML сервис для тестирования подключения.")
async def test_func(request: PromptRequest = Body(..., examples={
    "basic": {
        "summary": "Простой prompt",
        "value": {"prompt": "Привет, проверь подключение"}
    }
})):
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


@r.post(
    "/support/process",
    response_model=SupportResponse,
    summary="Принять обращение пользователя, создать тикет и поставить его в очередь",
    description="""
Принимает обращение от пользователя, создаёт Dialog, Message и Ticket в БД, а затем ставит тикет в оперативную очередь для дальнейшей обработки диспетчером.
""",
)
async def process_support_request(
    request: SupportRequest = Body(
        ...,
        examples={
            "web": {
                "summary": "Пример обращения из веб-интерфейса",
                "value": {
                    "user_message": "Не могу войти в почту, пишет неправильный пароль",
                    "user_id": "user_vitalka",
                    "timestamp": "2025-10-18T12:00:00",
                    "channel": "web"
                }
            }
        }
    )
):
    """Обработка входящего обращения: создание диалога, сообщения и тикета и добавление его в очередь."""
    print(f"[support/process] Получено обращение от {request.user_id}: {request.user_message[:200]}...")

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
        # очередь недоступна — тикет в БД есть; логируем ошибку и возвращаем ответ
        print(f"[support/process] Не удалось положить ticket {ticket_id} в очередь: {e}")

    return {"ticket_id": ticket_id, "dialog_id": dialog.id, "status": ticket.status}


@r.post("/simulate/start", summary="Запустить симуляцию входящих обращений", description="Запустить фоновую задачу-симулятор, которая подаёт обращения из файла requests.txt.")
async def simulate_start():
    started = await simulation_manager.start_simulation()
    if not started:
        return {"status": "already_running"}
    return {"status": "started"}


@r.post("/simulate/stop", summary="Остановить симуляцию", description="Остановить симулятор.")
async def simulate_stop():
    await simulation_manager.stop_simulation()
    return {"status": "stopped"}


@r.get("/simulate/status", summary="Статус симуляции", description="Текущий статус симуляции: запущена/остановлена, сколько отправлено.")
async def simulate_status():
    return simulation_manager.status()

@r.get("/statistic/all_count/{status_t}")
async def get_sum_of_tickets(status_t: str, db = db):
    return get_tickets_by_status(db, status_t).count()

@r.get("/statistic/time_spending")
async def spend_time(db=db):
    time = []
    for i in range(get_tickets_by_status(db, "all").count()):
        time.append(get_ticket_times(db, i).get("resolved_at") - get_ticket_times(db, i).get("created_at"))
    return sum(time)/ len(time)

@r.get("/statistic/cards/{status}")
async def get_tickets(status_t: str, db = db):
    return get_tickets_by_status(db, status_t)