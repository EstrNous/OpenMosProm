from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Boolean
)
from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False)
    status = Column(Enum("active", "closed", "escalated", name="dialog_status"), default="active")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    messages = relationship("Message", back_populates="dialog")
    ticket = relationship("Ticket", back_populates="dialog", uselist=False, cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="dialog", uselist=False)
    tool_invocations = relationship("ToolInvocation", back_populates="dialog")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    dialog_id = Column(Integer, ForeignKey("dialogs.id"))
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    is_relevant = Column(Boolean, default=True)

    dialog = relationship("Dialog", back_populates="messages")

class Ticket(Base):
    __tablename__ = "tickets"

    dialog_id = Column(Integer, ForeignKey("dialogs.id", ondelete="CASCADE"), primary_key=True)
    status = Column(Enum("solved", "in_progress", "escalated", name="ticket_status"), default="open")
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)
    type = Column(String, nullable=True)

    dialog = relationship("Dialog", back_populates="ticket")

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    dialog_id = Column(Integer, ForeignKey("dialogs.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    dialog = relationship("Dialog", back_populates="feedback")

class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    invocations = relationship("ToolInvocation", back_populates="tool")

class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(Integer, ForeignKey("tools.id"))
    dialog_id = Column(Integer, ForeignKey("dialogs.id"))
    parameters = Column(JSON)
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)

    tool = relationship("Tool", back_populates="invocations")
    dialog = relationship("Dialog", back_populates="tool_invocations")

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    dialog_id = Column(Integer, ForeignKey("dialogs.id"), nullable=True)
    success = Column(Boolean, default=True)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
