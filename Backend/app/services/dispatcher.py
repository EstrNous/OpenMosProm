# Backend/services/dispatcher.py
import os
import asyncio
import logging
import time
from typing import Optional, Dict, Any

import httpx

from .ticket_queue import ticket_queue
from Backend.crud import base_crud
from Backend.db.models import Ticket as TicketModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

logger = logging.getLogger("dispatcher")

MAX_CONCURRENCY = int(os.getenv("DISPATCHER_MAX_CONCURRENCY", "5"))
WORKER_POLL_SLEEP = float(os.getenv("DISPATCHER_POLL_SLEEP", "0.5"))  # для пустой очереди
ML_API_URL = os.getenv("ML_API_URL")
ML_API_TICKET_ENDPOINT = os.getenv("ML_API_TICKET_ENDPOINT", "/api/agent/process_ticket")
ML_REQUEST_TIMEOUT = float(os.getenv("ML_REQUEST_TIMEOUT", "10.0"))  # HTTP POST в ML
WORKER_DEQUEUE_TIMEOUT = float(os.getenv("WORKER_DEQUEUE_TIMEOUT", "1.0"))  # время ожидания для взятия из очереди

class Dispatcher:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        if self._running:
            return
        logger.info("Запущен Dispatcher (max concurrency=%s)", MAX_CONCURRENCY)
        self._running = True

        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Dispatcher stopped")

    async def _loop(self):
        # Основной цикл: пытаемся брать тикеты из очереди. Спим, если тикетов нет
        while self._running:
            try:
                # Try to dequeue a ticket (wait a little)
                ticket_id = await ticket_queue.dequeue(worker_id="dispatcher", wait=True, timeout=WORKER_DEQUEUE_TIMEOUT)
                if ticket_id is None:
                    await asyncio.sleep(WORKER_POLL_SLEEP)
                    continue

                # Acquire concurrency slot and run worker task
                await self._semaphore.acquire()
                asyncio.create_task(self._run_worker(ticket_id))

            except Exception as e:
                logger.exception("Dispatcher loop error: %s", e)
                await asyncio.sleep(1.0)

    async def _run_worker(self, ticket_id: int):
        """
        Worker: создаёт payload для ML и отправляет его.
        При ошибке заново отправляет в очередь.
        """
        try:
            db = SessionLocal()
            try:
                ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
                if not ticket:
                    logger.error("Ticket %s not found in DB; skipping (will requeue)", ticket_id)
                    await ticket_queue.enqueue_existing(ticket_id)
                    return

                # Получим сообщения диалога (если доступны через CRUD)
                messages = []
                try:
                    messages_objs = base_crud.get_messages_by_dialog(db, ticket.dialog_id)
                    for m in messages_objs:
                        messages.append({"id": m.id, "content": m.content, "timestamp": str(m.timestamp), "is_relevant": m.is_relevant})
                except Exception:
                    # если CRUD ломается, то ставим пустой список
                    messages = []

                payload = {
                    "ticket_id": ticket.id,
                    "dialog_id": ticket.dialog_id,
                    "ticket_type": getattr(ticket, "type", None),
                    "created_at": str(ticket.created_at),
                    "messages": messages,
                }
            finally:
                db.close()

            # ML endpoint
            if not ML_API_URL:
                # requeue and log
                logger.error("ML_API_URL not configured; requeue ticket %s", ticket_id)
                await ticket_queue.enqueue_existing(ticket_id)
                return

            ml_url = ML_API_URL.rstrip("/") + ML_API_TICKET_ENDPOINT

            # Отправка в ML - мы не ждём решение тикета, а просто ответ "accepted" или что-то такое
            async with httpx.AsyncClient(timeout=ML_REQUEST_TIMEOUT) as client:
                resp = await client.post(ml_url, json=payload)
                resp.raise_for_status()
                logger.info("Sent ticket %s to ML; ML responded status=%s", ticket_id, resp.status_code)

        except Exception as e:
            logger.exception("Worker failed for ticket %s: %s", ticket_id, e)
            try:
                await asyncio.sleep(0.2)
                await ticket_queue.enqueue_existing(ticket_id)
            except Exception:
                logger.exception("Failed to requeue ticket %s after worker failure", ticket_id)
        finally:
            try:
                self._semaphore.release()
            except Exception:
                pass

dispatcher = Dispatcher()
