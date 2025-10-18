# Backend/services/ticket_queue.py
import asyncio
import os
import time
from typing import Optional, Dict, Any
from Backend.db.session import get_db

from Backend.db.models import Ticket
from Backend.crud import base_crud


# Конфиги
VISIBILITY_TIMEOUT = int(os.getenv("TICKET_VISIBILITY_TIMEOUT", "60"))  # сек
REQUEUE_CHECK_PERIOD = float(os.getenv("TICKET_REQUEUE_CHECK_PERIOD", "5.0"))  # сек
db = get_db()

class InMemoryTicketQueue:
    def __init__(self):
        self._q: asyncio.Queue[int] = asyncio.Queue()
        self._in_progress: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # это чтобы по дурости не отредачить одну и ту же запись
        self._requeue_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self, preload_from_db: bool = True):
        """Запускаем фоновую задачу по проверке вхождения новых тикетов. По умолчанию подгружаем open-тикеты из БД."""
        if self._running:
            return
        self._running = True
        if preload_from_db:
            await self._preload_open_tickets_from_db()
        self._requeue_task = asyncio.create_task(self._requeue_monitor())

    async def stop(self):
        self._running = False
        if self._requeue_task:
            self._requeue_task.cancel()
            try:
                await self._requeue_task
            except asyncio.CancelledError:
                pass

    async def _preload_open_tickets_from_db(self):
        """Подгружаем open тикеты из БД (порядок по возрастанию даты создания)."""
        try:
            qs = db.query(Ticket).filter(Ticket.status == "open").order_by(Ticket.created_at.asc()).all()
            for t in qs:
                await self._q.put(t.id)
        finally:
            db.close()

    async def enqueue_new(self, dialog_id: int, type: Optional[str] = None) -> int:
        """
        Создаёт тикет в БД и ставит его в очередь.
        Возвращает ticket_id.
        """
        try:
            ticket = base_crud.create_ticket(db, dialog_id=dialog_id, type=type)
            ticket_id = ticket.id
        finally:
            db.close()

        await self._q.put(ticket_id)
        return ticket_id

    async def enqueue_existing(self, ticket_id: int):
        """Положить в очередь уже существующий ticket_id"""
        await self._q.put(ticket_id)

    async def dequeue(self, worker_id: Optional[str] = None, wait: bool = True, timeout: Optional[float] = None) -> Optional[int]:
        """
        Забирает ticket_id из очереди. и помечает его как in_progress.
        """
        try:
            if wait:
                ticket_id = await asyncio.wait_for(self._q.get(), timeout=timeout)
            else:
                ticket_id = self._q.get_nowait()
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

        # помечаем in_progress
        async with self._lock:
            self._in_progress[ticket_id] = {"worker": worker_id or "anon", "ts": time.time()}

        # обновим статус в БД в отдельной подсессии
        try:
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if t:
                t.status = "in_progress"
                db.add(t)
                db.commit()
                db.refresh(t)
        finally:
            db.close()

        return ticket_id

    async def get_result(self, ticket_id: int, result_payload: Optional[dict] = None, solved: bool = True):
        """
        ML сообщает, что работа с тикетом закончена.
        - удаляем из in_progress
        - обновляем запись в БД: если solved -> status=solved/closed/resolved_at
        """
        async with self._lock:
            if ticket_id in self._in_progress:
                del self._in_progress[ticket_id]
            else:
                pass

        # Обновление в БД
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return False
            if solved:
                base_crud.close_ticket(db, ticket_id=ticket_id, type=ticket.type)
            else:
                ticket.status = "escalated"
                db.add(ticket)
                db.commit()
                db.refresh(ticket)
        finally:
            db.close()
        return True

    async def peek(self) -> Optional[int]:
        """Посмотреть следующий ticket_id без извлечения."""
        # На самом деле в Queue посмотреть мы не можем, так что извлекаем тикет и закидываем его заново.
        try:
            ticket_id = self._q.get_nowait()
        except asyncio.QueueEmpty:
            return None

        await self._q.put(ticket_id)
        return ticket_id

    async def size(self) -> int:
        return self._q.qsize()

    async def in_progress_info(self) -> Dict[int, Dict[str, Any]]:
        async with self._lock:
            return dict(self._in_progress)

    async def _requeue_monitor(self):
        """Фоновая задача: проверяет истёкшие тикеты, которые in_progress, и возвращает их в очередь."""
        try:
            while self._running:
                now = time.time()
                to_requeue = []
                async with self._lock:
                    for tid, info in list(self._in_progress.items()):
                        if now - info["ts"] > VISIBILITY_TIMEOUT:
                            to_requeue.append(tid)
                            del self._in_progress[tid]

                # вернуть в очередь и обновить статус в БД
                if to_requeue:
                    try:
                        for tid in to_requeue:
                            await self._q.put(tid)
                            t = db.query(Ticket).filter(Ticket.id == tid).first()
                            if t:
                                t.status = "open"
                                db.add(t)
                        db.commit()
                    finally:
                        db.close()

                await asyncio.sleep(REQUEUE_CHECK_PERIOD)
        except asyncio.CancelledError:
            return

# singleton
ticket_queue = InMemoryTicketQueue()
