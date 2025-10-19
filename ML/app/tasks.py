import logging
import requests
import os
from celery import Celery
from celery.signals import worker_process_init
from .core.settings import setup_services
from .core import settings

BACKEND_CALLBACK_URL = os.getenv("BACKEND_CALLBACK_URL")
MAX_RETRIES = int(os.getenv("CELERY_MAX_RETRIES", 3))
RETRY_DELAY_SEC = int(os.getenv("CELERY_RETRY_DELAY_SEC", 300))

celery_app = Celery("ml_worker", broker="redis://redis:6379/0", backend="redis://redis:6379/0")


@worker_process_init.connect
def init_worker(**kwargs):
    try:
        settings.ensure_services_ready()
        logging.info("Celery worker: сервисы инициализированы.")
    except Exception as e:
        logging.error(f"Celery worker: ошибка инициализации сервисов: {e}", exc_info=True)


def send_callback_to_backend(dialog_id: str, status: str, ml_result: dict | None = None,
                             error_message: str | None = None):
    if not BACKEND_CALLBACK_URL:
        logging.error("Переменная BACKEND_CALLBACK_URL не задана! Не могу отправить результат.")
        return

    callback_payload = {
        "dialog_id": dialog_id,
        "status": status,
        "ml_result": ml_result,
        "error_message": error_message
    }

    from fastapi.encoders import jsonable_encoder

    try:
        logging.info(f"Отправка callback на бэкенд для тикета [{dialog_id}] со статусом '{status}'...")
        response = requests.post(BACKEND_CALLBACK_URL, json=jsonable_encoder(callback_payload), timeout=30)
        response.raise_for_status()
        logging.info(f"Callback для тикета [{dialog_id}] успешно отправлен.")
    except requests.RequestException as e:
        logging.error(f"Не удалось отправить callback для тикета [{dialog_id}]: {e}")


@celery_app.task(name="process_ticket_query", bind=True)
def process_ticket_query(self, user_query: str, dialog_id: str):
    try:
        logging.info(
            f"Воркер получил задачу для тикета [{dialog_id}] (попытка {self.request.retries + 1}/{MAX_RETRIES + 1})")

        settings.ensure_services_ready()

        if settings.agent_service_instance is None:
            raise RuntimeError("Agent service is not initialized")

        result = settings.agent_service_instance.process_query(user_query)

        result_with_query = result.copy()
        result_with_query['user_query'] = user_query

        send_callback_to_backend(dialog_id, "processed", ml_result=result_with_query)

        return {"status": "success"}

    except Exception as e:
        logging.error(f"Ошибка при обработке задачи для тикета [{dialog_id}] (попытка {self.request.retries + 1}): {e}",
                      exc_info=True)

        try:
            raise self.retry(exc=e, countdown=RETRY_DELAY_SEC, max_retries=MAX_RETRIES)
        except self.MaxRetriesExceededError:
            logging.error(
                f"Все {MAX_RETRIES + 1} попыток для тикета [{dialog_id}] провалены. Отправка статуса 'error' на бэкенд.")
            error_msg = f"Задача не выполнена после {MAX_RETRIES + 1} попыток. Последняя ошибка: {type(e).__name__}"
            send_callback_to_backend(dialog_id, "error", error_message=error_msg)
            raise
