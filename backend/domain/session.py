from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    ANONYMOUS = "anonymous"
    COLLECTING_IDENTITY = "collecting_identity"
    CODE_SENT = "code_sent"
    AWAITING_CODE = "awaiting_code"
    VERIFIED = "verified"
    ESCALATED_TO_HUMAN = "escalated_to_human"


@dataclass
class Session:
    session_id: str
    state: SessionState = SessionState.ANONYMOUS
    # Identity collection
    collected_fields: dict = field(default_factory=dict)
    # Pending verification (CODE_SENT / AWAITING_CODE)
    pending_customer_id: Optional[str] = None
    verification_code_hash: Optional[str] = None
    code_sent_at: Optional[datetime] = None
    attempt_count: int = 0
    # Authorized identity (VERIFIED only)
    verified_customer_id: Optional[str] = None
    # Escalation (cosmetic overlay)
    is_escalated: bool = False
    first_name_if_known: Optional[str] = None
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # DB reference
    chat_session_db_id: str = ""
    # Message history for LLM (kept in memory, not persisted between restarts)
    message_history: list[dict] = field(default_factory=list)


def transition_to_collecting_identity(session: Session) -> Session:
    """ANONYMOUS → COLLECTING_IDENTITY when user asks about shipment."""
    assert session.state in (SessionState.ANONYMOUS, SessionState.COLLECTING_IDENTITY)
    session.state = SessionState.COLLECTING_IDENTITY
    return session


def transition_to_code_sent(
    session: Session,
    pending_customer_id: str,
    code_hash: str,
    first_name: str,
) -> Session:
    """COLLECTING_IDENTITY → CODE_SENT after identity match."""
    assert session.state == SessionState.COLLECTING_IDENTITY
    session.state = SessionState.CODE_SENT
    session.pending_customer_id = pending_customer_id
    session.verification_code_hash = code_hash
    session.code_sent_at = datetime.now(timezone.utc)
    session.attempt_count = 0
    session.first_name_if_known = first_name
    return session


def transition_to_awaiting_code(session: Session) -> Session:
    """CODE_SENT → AWAITING_CODE once modal is shown."""
    assert session.state in (SessionState.CODE_SENT, SessionState.AWAITING_CODE)
    session.state = SessionState.AWAITING_CODE
    return session


def transition_to_verified(session: Session) -> Session:
    """AWAITING_CODE → VERIFIED after correct code."""
    assert session.state == SessionState.AWAITING_CODE
    assert session.pending_customer_id is not None
    session.state = SessionState.VERIFIED
    # SECURITY: copy pending to verified, then clear pending
    session.verified_customer_id = session.pending_customer_id
    session.pending_customer_id = None
    session.verification_code_hash = None
    session.code_sent_at = None
    session.attempt_count = 0
    return session


def transition_to_collecting_after_failure(session: Session) -> Session:
    """Reset back to COLLECTING_IDENTITY after max attempts or expiry."""
    session.state = SessionState.COLLECTING_IDENTITY
    session.pending_customer_id = None
    session.verification_code_hash = None
    session.code_sent_at = None
    session.attempt_count = 0
    return session


def set_escalated(session: Session) -> Session:
    """Mark session as escalated (cosmetic — does not change gating state)."""
    session.is_escalated = True
    return session
