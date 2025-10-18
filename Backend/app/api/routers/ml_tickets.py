from typing import Optional, Literal, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from Backend.app.crud import base_crud
from Backend.app.db.models import Ticket, Tool
from Backend.app.db.session import get_db

logger = logging.getLogger("ml-callback")
router = APIRouter(prefix="/api/ml", tags=["ML"])

db = get_db()

class MLCallback(BaseModel):
    """
    Общая структура callback'а от ML.
    Ожидаем, что ML пришлёт ticket_id (наш dialog_id), action_type и payload.
    """
    ticket_id: int = Field(..., description="ID тикета (в нашей системе это dialog_id)")
    action_type: Literal["answer", "escalate", "call_tool"] = Field(..., description="Действие, которое предлагает ML")
    payload: Optional[Dict[str, Any]] = Field(None, description="Содержимое результата — зависит от action_type")
    user_query: Optional[str] = Field(None, description="Оригинальный вопрос пользователя")


@router.post(
    "/tickets/result",
    summary="Callback от ML: результат обработки тикета",
    description="""
ML вызывает этот endpoint, чтобы сообщить результат по ticket_id.

Поддерживаемые action_type:
- `answer` — ML прислал ответ
- `escalate` — ML просит эскалации
- `call_tool` — ML просит выполнить инструмент

В теле обязательно `ticket_id` (в нашей модели это dialog_id).
""",
)
async def ticket_result(payload: MLCallback = Body(
        ...,
        examples={
            "answer": {
                "summary": "Пример обычного ответа",
                "value": {
                    "ticket_id": 123,
                    "action_type": "answer",
                    "payload": {
                        "answer_text": "1) Сделайте X\n2) Сделайте Y",
                        "sources": [
                            {"filename": "vpn_macos_fix.md", "score": 0.74}
                        ]
                    },
                    "user_query": "как починить впн на маке?"
                }
            },
            "escalate": {
                "summary": "Пример эскалации",
                "value": {
                    "ticket_id": 124,
                    "action_type": "escalate",
                    "payload": {
                        "reason": "requires_manual_verification",
                        "note": "Нужно подключить администратора"
                    }
                }
            },
            "call_tool": {
                "summary": "Пример вызова инструмента",
                "value": {
                    "ticket_id": 125,
                    "action_type": "call_tool",
                    "payload": {
                        "tool_name": "reset_password",
                        "parameters": {"user_id": "user_123"}
                    }
                }
            }
        }
    ),
):
    """
    Обрабатываем callback от ML в зависимости от action_type.
    Для надёжности: записываем raw-result в логи (таблица logs), затем переходим в одну из веток:
      - answer: создаём message с текстом ответа и закрываем тикет (placeholder).
      - escalate: помечаем тикет как escalated и логируем.
      - call_tool: создаём (если нужно) запись о вызове инструмента и логируем.
    """
    dialog_id = payload.ticket_id

    # Проверим, что такой тикет существует
    ticket = db.query(Ticket).filter(Ticket.dialog_id == dialog_id).first()
    if not ticket:
        logger.warning("ML callback: ticket/dialog_id %s not found", dialog_id)
        raise HTTPException(status_code=404, detail="Ticket (dialog) not found")

    # Сохранить результат в логах
    try:
        base_crud.create_log(db, event_type="ml_result", dialog_id=dialog_id, success=True, details=payload.dict())
    except Exception as e:
        logger.exception("Failed to write ml_result log for dialog %s: %s", dialog_id, e)

    action = payload.action_type

    # --- Branch: answer ---
    if action == "answer":
        answer_text = None
        if payload.payload:
            # ожидаем answer_text
            answer_text = payload.payload.get("answer_text") or payload.payload.get("text") or None

        # Заглушка: создаём сообщение с ответом в диалоге и закрываем тикет
        if answer_text:
            try:
                base_crud.create_message(db, dialog_id=dialog_id, content=answer_text)
            except Exception:
                logger.exception("Failed to create message (answer) for dialog %s", dialog_id)

        # Закрываем тикет
        try:
            base_crud.close_ticket(db, dialog_id=dialog_id, type=ticket.type if hasattr(ticket, "type") else None)
        except Exception:
            logger.exception("Failed to close ticket for dialog %s", dialog_id)

        logger.info("ML action 'answer' handled for dialog %s", dialog_id)
        return {"status": "ok", "action": "answer"}

    # --- Branch: escalate ---
    if action == "escalate":
        # Отметим тикет как escalated и создадим лог (заглушка)
        try:
            ticket.status = "escalated"
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
        except Exception:
            logger.exception("Failed to mark ticket as escalated for dialog %s", dialog_id)

        logger.info("ML action 'escalate' handled for dialog %s", dialog_id)
        return {"status": "ok", "action": "escalate"}

    # --- Branch: call_tool ---
    if action == "call_tool":
        tool_name = None
        parameters = {}
        if payload.payload:
            tool_name = payload.payload.get("tool_name")
            parameters = payload.payload.get("parameters", {})

        if not tool_name:
            logger.warning("call_tool without tool_name for dialog %s", dialog_id)
            raise HTTPException(status_code=400, detail="tool_name required for call_tool action")

        try:
            # пытаемся найти существующий Tool
            tool_obj = db.query(Tool).filter(Tool.name == tool_name).first()
            if not tool_obj:
                tool_obj = base_crud.create_tool(db, name=tool_name, description=None)
        except Exception:
            logger.exception("Failed to get or create Tool %s", tool_name)
            raise HTTPException(status_code=500, detail="internal error creating tool")

        # Создаём запись вызова инструмента (ToolInvocation) — result пока пустой
        try:
            invocation = base_crud.create_tool_invocation(db,
                                                         tool_id=tool_obj.id,
                                                         dialog_id=dialog_id,
                                                         parameters=parameters,
                                                         result={})
        except Exception:
            logger.exception("Failed to create tool invocation for dialog %s", dialog_id)
            raise HTTPException(status_code=500, detail="failed to create tool invocation")

        # Не закрываем тикет автоматически — ML/инструмент/оператор решит
        logger.info("ML action 'call_tool' handled for dialog %s (tool=%s)", dialog_id, tool_name)
        return {"status": "ok", "action": "call_tool", "invocation_id": invocation.id}

    # --- Unknown action_type ---
    logger.warning("Unknown action_type '%s' from ML for dialog %s", action, dialog_id)
    raise HTTPException(status_code=400, detail=f"Unknown action_type: {action}")
