import os
import asyncio
from .simulator import UserSimulator

REQUESTS_FILE = os.getenv("REQUESTS_FILE", "Backend/data/requests.txt")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

simulator = UserSimulator(requests_file=REQUESTS_FILE, backend_url=BACKEND_URL)

_sim_task: asyncio.Task | None = None

async def start_simulation() -> bool:
    """Запускает симуляцию, если она ещё не запущена. Возвращает True, если симуляция была успешно запущена."""
    global _sim_task
    if _sim_task and not _sim_task.done():
        return False

    # создаём фоновую задачу
    _sim_task = asyncio.create_task(simulator.start_simulation())
    return True

async def stop_simulation() -> bool:
    """Останавливает симуляцию. Возвращает True после остановки/ожидания завершения."""
    global _sim_task
    simulator.stop_simulation()
    if _sim_task:
        try:
            await _sim_task
        except asyncio.CancelledError:
            pass
    return True

def status() -> dict:
    return {
        "is_running": bool(simulator.is_running),
        "sent_count": simulator.sent_count,
        "queue_size": len(simulator.requests) if simulator.requests is not None else 0
    }