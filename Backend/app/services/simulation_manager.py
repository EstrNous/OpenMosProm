# app/services/simulation_manager.py
import os
import asyncio
import logging
from .simulator import UserSimulator
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger("simulation-manager")

if not logger.handlers:
    import sys
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(stream=sys.stdout, level=log_level,
                        format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

REQUESTS_FILE = os.getenv("REQUESTS_FILE", "app/data/requests.txt")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# создаём симулятор
simulator = UserSimulator(requests_file=REQUESTS_FILE, backend_url=BACKEND_URL,
                          min_interval=float(os.getenv("INTERVAL_LOWER", 0.5)),
                          max_interval=float(os.getenv("INTERVAL_UPPER", 2.0)))

_sim_task: asyncio.Task | None = None

async def start_simulation() -> bool:
    """Запускает симуляцию, если она ещё не запущена. Возвращает True, если запущена."""
    global _sim_task
    if _sim_task and not _sim_task.done():
        logger.warning("Simulation already running (task=%s).", _sim_task)
        return False

    logger.info("Starting simulation (requests_file=%s backend_url=%s)", REQUESTS_FILE, BACKEND_URL)
    # создаём фоновую задачу
    _sim_task = asyncio.create_task(simulator.start_simulation())
    return True

async def stop_simulation() -> bool:
    """Останавливает симуляцию и ждёт завершения."""
    global _sim_task
    logger.info("Stopping simulation (if running).")
    simulator.stop_simulation()
    if _sim_task:
        try:
            await _sim_task
        except asyncio.CancelledError:
            logger.info("Simulation task cancelled.")
        except Exception:
            logger.exception("Exception while awaiting simulation task.")
    return True

def status() -> dict:
    info = {
        "is_running": bool(simulator.is_running),
        "sent_count": simulator.sent_count,
        "loaded_requests": len(simulator.requests) if simulator.requests is not None else 0,
        "backend_url": BACKEND_URL
    }
    logger.debug("Simulation status requested: %s", info)
    return info
