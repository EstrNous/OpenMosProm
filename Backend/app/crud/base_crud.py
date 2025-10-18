from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from Backend.app.db.models import (
    Dialog, Message, Ticket, Feedback, Tool, ToolInvocation, Log
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

def create_message(db: Session, dialog_id: int, content: str) -> Message:
    message = Message(dialog_id=dialog_id, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages_by_dialog(db: Session, dialog_id: int) -> list[Message]:
    return db.query(Message).filter(Message.dialog_id == dialog_id).order_by(Message.timestamp).all()

def create_ticket(db: Session, dialog_id: int, type: str | None = None) -> Ticket:
    ticket = Ticket(dialog_id=dialog_id, type=type)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def close_ticket(db: Session, dialog_id: int, type: str | None = None) -> Ticket | None:
    ticket = db.query(Ticket).filter(Ticket.dialog_id == dialog_id).first()
    if ticket:
        ticket.status = "closed"
        ticket.type = type
        ticket.resolved_at = datetime.now()
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
    return ticket

def get_tickets_by_status(db: Session, status: str | None = None) -> list[Ticket]:
    query = db.query(Ticket)

    if status and status.lower() != "all":
        query = query.filter(Ticket.status == status)

    return query.order_by(Ticket.created_at.desc()).all()

def get_tickets_by_type(db: Session, ticket_type: str) -> list[Ticket]:
    return db.query(Ticket).filter(Ticket.type == ticket_type).all()

def get_ticket_times(db: Session, dialog_id: int) -> dict | None:
    ticket = db.query(Ticket).filter(Ticket.dialog_id == dialog_id).first()

    if not ticket:
        return None

    return {
        "id": ticket.dialog_id,
        "created_at": ticket.created_at,
        "resolved_at": ticket.resolved_at
    }

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


def get_invocations_by_dialog(db: Session, dialog_id: int) -> list[ToolInvocation]:
    return db.query(ToolInvocation).filter(ToolInvocation.dialog_id == dialog_id).all()

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

def peek_next_open_ticket(db: Session) -> Ticket | None:
    """
    Возвращает самый старый тикет со статусом, отличным от 'in_progress'/'closed' (т.е. open),
    не модифицируя его. FIFO по created_at.
    """
    stmt = select(Ticket).where(Ticket.status == "open").order_by(Ticket.created_at.asc()).limit(1)
    res = db.execute(stmt).scalars().first()
    return res

def pop_next_ticket(db: Session) -> Ticket | None:
    """
    Извлекает самый старый open тикет и помечает его 'in_progress'.
    Возвращает тикет или None, если очередь пуста.
    Для прода нужно делать это в транзакции/с блокировкой.
    """
    # Находим старейший open тикет
    ticket = peek_next_open_ticket(db)
    if not ticket:
        return None

    # Помечаем как in_progress
    ticket.status = "in_progress"

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket