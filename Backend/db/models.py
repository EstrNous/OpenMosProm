from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_base
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    CLIENT = "client"
    OPERATOR = "operator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    dialogs: Mapped[list["Dialog"]] = relationship("Dialog", back_populates="user")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")
    operated_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="operator", foreign_keys="Ticket.operator_id"
    )
    tool_invocations: Mapped[list["ToolInvocation"]] = relationship("ToolInvocation", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

class DialogStatus(enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ESCALATED = "escalated"


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[DialogStatus] = mapped_column(Enum(DialogStatus), default=DialogStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ticket_id: Mapped[UUID | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="dialogs")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="dialog")
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="dialog", uselist=False)
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="dialog")
    tool_invocations: Mapped[list["ToolInvocation"]] = relationship("ToolInvocation", back_populates="dialog")

    def __repr__(self):
        return f"<Dialog id={self.id} user={self.user_id} status={self.status}>"

class SenderType(enum.Enum):
    USER = "user"
    AGENT = "agent"
    OPERATOR = "operator"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dialog_id: Mapped[UUID] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=True)

    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.sender_type}: {self.content[:30]}>"

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Ticket(Base):
    __tablename__ = "tickets"

    dialog_id: Mapped[UUID] = mapped_column(ForeignKey("dialogs.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    operator_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="tickets", foreign_keys=[user_id])
    operator: Mapped["User"] = relationship("User", back_populates="operated_tickets", foreign_keys=[operator_id])
    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="ticket")

    def __repr__(self):
        return f"<Ticket id={self.id} status={self.status}>"

class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    invocations: Mapped[list["ToolInvocation"]] = relationship("ToolInvocation", back_populates="tool")

    def __repr__(self):
        return f"<Tool {self.name}>"

class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tool_id: Mapped[UUID] = mapped_column(ForeignKey("tools.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    dialog_id: Mapped[UUID | None] = mapped_column(ForeignKey("dialogs.id"), nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tool: Mapped["Tool"] = relationship("Tool", back_populates="invocations")
    user: Mapped["User"] = relationship("User", back_populates="tool_invocations")
    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="tool_invocations")

    def __repr__(self):
        return f"<ToolInvocation {self.tool_id}>"

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dialog_id: Mapped[UUID] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column()  # +1 или -1
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="feedbacks")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<Feedback {self.rating} for dialog {self.dialog_id}>"

class LogEventType(enum.Enum):
    MESSAGE_SENT = "message_sent"
    TICKET_CREATED = "ticket_created"
    TOOL_INVOKED = "tool_invoked"
    FEEDBACK_GIVEN = "feedback_given"

class LogEvent(Base):
    __tablename__ = "logs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[LogEventType] = mapped_column(Enum(LogEventType))
    dialog_id: Mapped[UUID | None] = mapped_column(ForeignKey("dialogs.id"), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LogEvent {self.event_type} success={self.success}>"
