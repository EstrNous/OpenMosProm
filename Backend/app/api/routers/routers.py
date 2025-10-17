import os
import httpx
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, status, WebSocket
from dotenv import load_dotenv
from Backend.app.schemas import PromptRequest, SimpleAnswer, SupportRequest
from Backend.app.services import simulation_manager

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

@r.get("/statistic")
async def get_counts_of_tickets():
    return {"message": "Обратился к Витале"}