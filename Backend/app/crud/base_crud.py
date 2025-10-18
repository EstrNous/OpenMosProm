from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from ..db.models import (
    Dialog, Message, Feedback, Tool, ToolInvocation, Log
)

def create_dialog(db: Session, session_id: str) -> Dialog:
    dialog = Dialog(session_id=session_id)
    db.add(dialog)
    db.commit()
    db.refresh(dialog)
    return dialog


def get_dialog(db: Session, dialog_id: int) -> Dialog | None:
    return db.query(Dialog).filter(Dialog.id == dialog_id).first()


def update_dialog_status(db: Session, dialog_id: int, status: str) -> Dialog | None:
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if dialog:
        dialog.status = status
        dialog.updated_at = datetime.now()
        db.commit()
        db.refresh(dialog)
    return dialog

def close_dialog(db: Session, dialog_id: int, type: str | None = None) -> Dialog | None:
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if dialog:
        dialog.status = "closed"
        dialog.type = type
        dialog.resolved_at = datetime.now()
        dialog.updated_at = datetime.now()
        db.commit()
        db.refresh(dialog)
    return dialog

def get_dialogs_by_status(db: Session, status: str | None = None) -> list[Dialog]:
    query = db.query(Dialog)
    if status and status.lower() != "all":
        query = query.filter(Dialog.status == status)
    return query.order_by(Dialog.created_at.desc()).all()

def get_dialogs_by_type(db: Session, dialog_type: str) -> list[Dialog]:
    return db.query(Dialog).filter(Dialog.type == dialog_type).all()

def get_dialog_times(db: Session, dialog_id: int) -> dict | None:
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if not dialog:
        return None
    return {
        "id": dialog.id,
        "created_at": dialog.created_at,
        "resolved_at": dialog.resolved_at
    }

def create_message(db: Session, dialog_id: int, content: str) -> Message:
    message = Message(dialog_id=dialog_id, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def create_feedback(db: Session, dialog_id: int, rating: int, comment: str | None = None) -> Feedback:
    feedback = Feedback(dialog_id=dialog_id, rating=rating, comment=comment)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_by_dialog(db: Session, dialog_id: int) -> Feedback | None:
    return db.query(Feedback).filter(Feedback.dialog_id == dialog_id).first()

def create_tool(db: Session, name: str, description: str | None = None) -> Tool:
    tool = Tool(name=name, description=description)
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def get_all_tools(db: Session) -> list[Tool]:
    return db.query(Tool).order_by(Tool.created_at).all()

def create_tool_invocation(db: Session, tool_id: int, dialog_id: int, parameters: dict, result: dict) -> ToolInvocation:
    invocation = ToolInvocation(
        tool_id=tool_id,
        dialog_id=dialog_id,
        parameters=parameters,
        result=result
    )
    db.add(invocation)
    db.commit()
    db.refresh(invocation)
    return invocation

def get_all_tool_invocations(db: Session):
    return db.query(ToolInvocation).all()

def get_invocations_by_dialog(db: Session, dialog_id: int) -> list[ToolInvocation]:
    return db.query(ToolInvocation).filter(ToolInvocation.dialog_id == dialog_id).all()


def get_tool_invocations(db: Session, tool_id: int):
    return db.query(ToolInvocation).filter(ToolInvocation.tool_id == tool_id)


def create_log(db: Session, event_type: str, dialog_id: int | None = None, success: bool = True, details: dict | None = None) -> Log:
    log = Log(
        event_type=event_type,
        dialog_id=dialog_id,
        success=success,
        details=details or {}
    )
    db.add(log)
    db.commit()
    return log


def get_logs(db: Session, event_type: str | None = None) -> list[Log]:
    query = db.query(Log)
    if event_type:
        query = query.filter(Log.event_type == event_type)
    return query.order_by(Log.created_at.desc()).all()
