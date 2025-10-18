from datetime import datetime

from fastapi import APIRouter, HTTPException, Body, Depends
import logging

from sqlalchemy.orm import Session

from ...crud import base_crud
from ...schemas import MLWorkerResult
from ...db.models import Dialog
from ...db.session import get_db


logger = logging.getLogger("ml-callback")
router = APIRouter(prefix="/api/ml", tags=["ML"])
db = get_db()


@router.post("dialogs/result", summary="Callback от ML-воркера: результат обработки диалога")
async def dialogs_result(payload: MLWorkerResult = Body(...), db: Session = Depends(get_db)):
    """
    Обработка callback'а от ML-воркера в формате, который присылает ML-команда.
    1) Проверяем существование диалога.
    2) Пишем raw-result в logs.
    3) В зависимости от payload.status и payload.ml_result.action_type выполняем нужные действия:
       - processed + answer: создаём message с summary, пытаемся закрыть диалог.
       - processed + escalate: создаём message с summary, помечаем escalated.
       - processed + call_tool: создаём/находим Tool и создаём ToolInvocation (не закрываем диалог).
       - error: помечаем ticket.ml_error (если недоступно, fallback -> escalated) и записываем error_message.
    """
    dialog_id = payload.dialog_id

    dialog = db.query(Dialog).filter(Dialog.dialog_id == dialog_id).first()
    if not dialog:
        logger.warning("ML callback: ialog_id %s not found", dialog_id)
        raise HTTPException(status_code=404, detail="Dialog not found")

    try:
        base_crud.create_log(db,
                             event_type="ml_result",
                             dialog_id=dialog_id,
                             success=(payload.status == "processed"),
                             details={
                                 "ml_result": payload.ml_result,
                                 "error_message": payload.error_message,
                                 "received_at": datetime.now().isoformat()
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

        dialog.status = "escalated"
        db.add(dialog)
        db.commit()
        db.refresh(dialog)
        logger.info("Dialog %s marked as escalated because of ML_ERROR", dialog_id)

        return {"status": "ok", "action": "error_handled"}

    # Далее — payload.status == "processed"
    ml_result = payload.ml_result if payload.ml_result else {}
    action_type = ml_result.get("action_type")
    ml_payload = ml_result.get("payload", {}) if isinstance(ml_result, dict) else {}

    # Branch: answer
    if action_type == "answer":
        # Ожидаем: payload.category, payload.summary (предложенный ответ), payload.sources (опционально)
        category = ml_payload.get("category")
        summary = ml_payload.get("summary") or ""
        # 1) Создаём сообщение с предложенным ответом (summary)
        if summary:
            try:
                base_crud.create_message(db, dialog_id=dialog_id, content=f"[Auto-answer by ML]\n{summary}")
            except Exception:
                logger.exception("Failed to create auto-answer message for dialog %s", dialog_id)
        # 2)  Помечаем диалог как решённый: closed + status
        dialog.status = "closed"
        dialog_id.resolved_at = datetime.now()
        db.add(dialog)
        db.commit()
        db.refresh(dialog)
        logger.info("Dialog %s marked as solved by ML.", dialog_id)

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
            dialog.status = "escalated"
            db.add(dialog)
            db.commit()
            db.refresh(dialog)
            logger.info("Dialog %s marked as escalated by ML.", dialog_id)
        except Exception:
            logger.exception("Failed to set dialog %s to escalated", dialog_id)

        return {"status": "ok", "action": "escalate"}

    # Если action_type не распознан или пуст
    logger.warning("Unknown or missing action_type in ml_result for dialog %s: %s", dialog_id, action_type)
    # Просто логируем (raw ml_result уже в логах) и возвращаем 400
    raise HTTPException(status_code=400, detail="Unknown or missing action_type in ml_result")
