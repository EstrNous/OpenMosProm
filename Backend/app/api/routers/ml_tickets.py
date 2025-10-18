from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Body, Depends
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...crud import base_crud
from ...schemas import MLCallback, MLWorkerResult
from ...db.models import Ticket, Tool
from ...db.session import get_db


logger = logging.getLogger("ml-callback")
router = APIRouter(prefix="/api/ml", tags=["ML"])
db = get_db()


@router.post("/result", summary="Callback от ML-воркера: результат обработки тикета")
async def tickets_result(payload: MLWorkerResult = Body(...), db: Session = Depends(get_db)):
    """
    Обработка callback'а от ML-воркера в формате, который присылает ML-команда.
    1) Проверяем существование тикета (Ticket привязан к dialog_id).
    2) Пишем raw-result в logs.
    3) В зависимости от payload.status и payload.ml_result.action_type выполняем нужные действия:
       - processed + answer: создаём message с summary, пытаемся закрыть тикет.
       - processed + escalate: создаём message с summary, помечаем escalated.
       - processed + call_tool: создаём/находим Tool и создаём ToolInvocation (не закрываем тикет).
       - error: помечаем ticket.ml_error (если недоступно, fallback -> escalated) и записываем error_message.
    """
    dialog_id = payload.ticket_id

    ticket = db.query(Ticket).filter(Ticket.dialog_id == dialog_id).first()
    if not ticket:
        logger.warning("ML callback: ticket/dialog_id %s not found", dialog_id)
        raise HTTPException(status_code=404, detail="Ticket (dialog) not found")

    try:
        base_crud.create_log(db,
                             event_type="ml_result",
                             dialog_id=dialog_id,
                             success=(payload.status == "processed"),
                             details={
                                 "ml_result": payload.ml_result,
                                 "error_message": payload.error_message,
                                 "received_at": datetime.utcnow().isoformat()
                             })
    except Exception:
        logger.exception("Failed to persist ml_result log for dialog %s", dialog_id)

    # Если ML сообщил об ошибке
    if payload.status == "error":
        # Сохраним сообщение в dialog (для видимости на дашборде)
        if payload.error_message:
            try:
                base_crud.create_message(db, dialog_id=dialog_id, content=f"[ML ERROR] {payload.error_message}")
            except Exception:
                logger.exception("Failed to create error message for dialog %s", dialog_id)

        # Попытаемся выставить статус "ml_error", но сделаем fallback на "escalated" если БД не примет значение
        try:
            ticket.status = "ml_error"
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            logger.info("Ticket %s marked as ml_error", dialog_id)
        except SQLAlchemyError as e:
            # Если enum/constraint не позволяет такое значение, переключаем на escalated и логируем
            logger.warning("Could not set status 'ml_error' for ticket %s (db error: %s). Falling back to 'escalated'.", dialog_id, e)
            try:
                ticket.status = "escalated"
                db.add(ticket)
                db.commit()
                db.refresh(ticket)
            except Exception:
                logger.exception("Failed to set fallback status for ticket %s", dialog_id)

        return {"status": "ok", "action": "error_handled"}

    # Далее — payload.status == "processed"
    ml_result = payload.ml_result or {}
    action_type = ml_result.get("action_type")
    ml_payload = ml_result.get("payload", {}) if isinstance(ml_result, dict) else {}

    # Branch: answer
    if action_type == "answer":
        # Ожидаем: payload.category, payload.summary (предложенный ответ), payload.sources (опционально)
        category = ml_payload.get("category")
        summary = ml_payload.get("summary") or ml_payload.get("answer_text") or ""
        # 1) Создаём сообщение с предложенным ответом (summary)
        if summary:
            try:
                base_crud.create_message(db, dialog_id=dialog_id, content=f"[Auto-answer by ML]\n{summary}")
            except Exception:
                logger.exception("Failed to create auto-answer message for dialog %s", dialog_id)
        # 2) Пытаемся пометить тикет как решённый: resolved_at + status
        try:
            ticket.status = "solved"
            ticket.resolved_at = datetime.now()
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            logger.info("Ticket %s marked as solved by ML (answer).", dialog_id)
        except SQLAlchemyError as e:
            logger.warning("Failed to mark ticket %s as solved: %s", dialog_id, e)
            try:
                # fallback: пометим как escalated, но лог будет содержать ml_result
                ticket.status = "escalated"
                db.add(ticket)
                db.commit()
                db.refresh(ticket)
            except Exception:
                logger.exception("Failed fallback status update for ticket %s", dialog_id)

        # 3) лог дополнительной информации (category/sources) — уже записан в ml_result log выше
        return {"status": "ok", "action": "answer"}

    # Branch: escalate
    if action_type == "escalate":
        category = ml_payload.get("category")
        summary = ml_payload.get("summary") or ""
        reason = ml_payload.get("reason")
        # создаём сообщение-напоминание для оператора
        msg = "[ML Эскалация]\n"
        if summary:
            msg += summary
        if reason:
            msg += f"\nReason: {reason}"
        try:
            base_crud.create_message(db, dialog_id=dialog_id, content=msg)
        except Exception:
            logger.exception("Failed to create escalation message for dialog %s", dialog_id)

        # обновляем статус в БД
        try:
            ticket.status = "escalated"
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            logger.info("Ticket %s marked as escalated by ML.", dialog_id)
        except Exception:
            logger.exception("Failed to set ticket %s to escalated", dialog_id)

        return {"status": "ok", "action": "escalate"}

    # Branch: call_tool
    if action_type == "call_tool":
        # ожидаем payload.tool_name и payload.parameters
        tool_name = ml_payload.get("tool_name")
        parameters = ml_payload.get("parameters", {}) or {}
        if not tool_name:
            logger.warning("ML requested call_tool but didn't provide tool_name (dialog %s)", dialog_id)
            raise HTTPException(status_code=400, detail="tool_name required for call_tool action")

        # найти или создать инструмент
        try:
            tool_obj = db.query(Tool).filter(Tool.name == tool_name).first()
            if not tool_obj:
                tool_obj = base_crud.create_tool(db, name=tool_name, description=None)
        except Exception:
            logger.exception("Failed to find/create tool %s for dialog %s", tool_name, dialog_id)
            raise HTTPException(status_code=500, detail="internal error creating tool")

        # создаём запись вызова инструмента (ToolInvocation)
        try:
            invocation = base_crud.create_tool_invocation(db,
                                                         tool_id=tool_obj.id,
                                                         dialog_id=dialog_id,
                                                         parameters=parameters,
                                                         result={})
        except Exception:
            logger.exception("Failed to create tool invocation for dialog %s", dialog_id)
            raise HTTPException(status_code=500, detail="failed to create tool invocation")

        logger.info("Created tool invocation %s for dialog %s (tool=%s)", invocation.id, dialog_id, tool_name)
        # Тикет остаётся в текущем статусе (оператор/инструмент далее разберётся)
        return {"status": "ok", "action": "call_tool", "invocation_id": invocation.id}

    # Если action_type не распознан или пуст
    logger.warning("Unknown or missing action_type in ml_result for dialog %s: %s", dialog_id, action_type)
    # Просто логируем (raw ml_result уже в логах) и возвращаем 400
    raise HTTPException(status_code=400, detail="Unknown or missing action_type in ml_result")
