import uuid
import enum
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from db.engine import Base


class SessionState(str, enum.Enum):
    anonymous = "anonymous"
    collecting_identity = "collecting_identity"
    code_sent = "code_sent"
    awaiting_code = "awaiting_code"
    verified = "verified"
    escalated_to_human = "escalated_to_human"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    state: Mapped[SessionState] = mapped_column(
        SAEnum(SessionState), nullable=False, default=SessionState.anonymous, index=True
    )
    started_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
