import os
import httpx

from fastapi import APIRouter, HTTPException, status, Body, Depends, BackgroundTasks
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from ...schemas import PromptRequest, SimpleAnswer, SupportRequest, SupportResponse
from ...services import simulation_manager
from ...crud import base_crud
from ...crud.base_crud import get_all_tools, get_tool_invocations, get_dialogs_by_status
from ...db.session import get_db
from ...services.ml_client import send_ticket_to_ml

# Загружаем переменные окружения
load_dotenv()

r = APIRouter(tags=["Support"])
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
                f"{ML_API_URL}/api/agent/test-prompt",
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
    summary="Принять обращение пользователя и поставить в обработку",
    description="Создаёт Dialog и Message в БД и асинхронно отправляет тикет в ML."
)
async def process_support_request(
    request: SupportRequest = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Создаёт dialog и message, возвращает dialog_id
    и запускает BackgroundTask для отправки в ML.
    """
    print(f"[support/process] Получено обращение от {request.user_id}: {request.user_message[:200]}...")

    try:
        dialog = base_crud.create_dialog(db, session_id=f"{request.user_id}-{request.timestamp}")
        base_crud.create_message(db, dialog_id=dialog.id, content=request.user_message)
    except Exception as e:
        print(f"[support/process] Ошибка при создании диалога: {e}")
        raise HTTPException(status_code=500, detail="error creating ticket")

    # запускаем фоновую задачу: передаем dialog.id
    if background_tasks is not None:
        background_tasks.add_task(send_ticket_to_ml, dialog.id)
    else:
        raise HTTPException(status_code=404, detail="Background tasks are not found.")

    # Возвращаем ticket_id == dialog.id
    return {"dialog_id": dialog.id, "status": "active"}


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
async def get_sum_of_dialogs(status_t: str, db: Session = Depends(get_db)):
    return len(get_dialogs_by_status(db, status_t))

@r.get("/statistic/time_spending")
async def spend_time(db: Session = Depends(get_db)):
    time = []
    tickets = get_dialogs_by_status(db, "closed")
    for i in range(len(tickets)):
        time.append(tickets[i].resolved_at - tickets[i].created_at)
    if len(time) == 0:
        return None
    else:
        return sum(time)/ len(time)

@r.get("/statistic/cards/{status}")
async def get_dialogs(status_t: str, db: Session = Depends(get_db)):
    return get_dialogs_by_status(db, status_t)

@r.get("/statistic/tools")
async def get_tools(db: Session = Depends(get_db)):
    return get_all_tools(db)

@r.get("/statistic/tools/{tool_id}/invocations")
async def get_tool_invocations_count(tool_id: int, db: Session = Depends(get_db)):
    """
    Возвращает количество вызовов (invocations) для инструмента с id = tool_id.
    """
    # посчитаем invocations
    count = get_tool_invocations(db, tool_id).count()

    return {"tool_id": tool_id, "invocations_count": count}