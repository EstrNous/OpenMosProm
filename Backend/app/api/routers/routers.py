import os
import httpx
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv
from Backend.app.schemas import PromptRequest, SimpleAnswer, SupportRequest
from Backend.app.services import simulation_manager
from Backend.crud.base_crud import get_ticket_times, get_tickets_by_status

# Загружаем переменные окружения
load_dotenv()

r = APIRouter()

db = Session # Здесь будет ссылка на сесиию постгре из .env преположительно
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

# Получение запроса от "пользователя"
@r.post("/support/process", response_model=SupportRequest)
async def process_support_request(request: SupportRequest):
    """Простой placeholder приёма обращений — симулятор POST'ит обращения сюда."""
    # Сюда бы надо очередь, логи, оркестратора и т.д.
    print(f"[support/process] Получено обращение от {request.user_id}: {request.user_message[:100]}...")
    return request

# --- Симулятор: старт/стоп/статус ---
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