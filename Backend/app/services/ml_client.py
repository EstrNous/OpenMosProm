import os
import asyncio
import logging
from typing import Any, Dict

import httpx
from ..db.models import Ticket
from ..crud import base_crud
from ..db.session import SessionLocal

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

ML_API_URL = os.getenv("ML_API_URL", "http://ml-api:8001")
ML_API_TICKET_ENDPOINT = os.getenv("ML_API_TICKET_ENDPOINT", "/submit-task")
ML_SEND_TIMEOUT = float(os.getenv("ML_SEND_TIMEOUT", "10.0"))
ML_MAX_RETRIES = int(os.getenv("ML_MAX_RETRIES", "2"))
ML_RETRY_BASE_DELAY = float(os.getenv("ML_RETRY_BASE_DELAY", "1.0"))

logger = logging.getLogger("ml-client")

async def _build_payload_for_dialog(dialog_id: int) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.dialog_id == dialog_id).first()
        if not ticket:
            return {}
        try:
            msg = base_crud.get_messages_by_dialog(db, ticket.dialog_id)[0].content
        except Exception:
            msg = ""
        payload = {
            "user_query": msg,
            "ticket_id": ticket.dialog_id
        }
        return payload
    finally:
        db.close()


async def send_ticket_to_ml(dialog_id: int) -> None:
    """
    Асинхронно отправляет ticket (идентифицированный dialog_id) в ML.
    """
    payload = await _build_payload_for_dialog(dialog_id)
    if not payload:
        logger.error("send_ticket_to_ml: dialog %s not found or payload empty", dialog_id)
        return

    if not ML_API_URL:
        logger.error("send_ticket_to_ml: ML_API_URL not configured; dialog %s not sent", dialog_id)
        return

    url = f"{ML_API_URL}/api/v1/agent/{ML_API_TICKET_ENDPOINT}"

    attempt = 0
    while attempt <= ML_MAX_RETRIES:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=ML_SEND_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                logger.info("send_ticket_to_ml: dialog=%s sent to ML (status=%s)", dialog_id, resp.status_code)
                return
        except Exception as e:
            logger.exception("send_ticket_to_ml: attempt %s failed for dialog %s: %s", attempt, dialog_id, e)
            if attempt > ML_MAX_RETRIES:
                logger.error("send_ticket_to_ml: giving up after %s attempts for dialog %s", attempt, dialog_id)
                return
            await asyncio.sleep(ML_RETRY_BASE_DELAY * (2 ** (attempt - 1)))
