import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import get_db
from domain.session import SessionState
from llm.tool_loop import run_tool_loop
from models.chat_session import ChatSession
from models.chat_session import SessionState as DBSessionState
from services.session_store import session_store

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateSessionResponse(BaseModel):
    session_id: str
    state: str


class ChatRequest(BaseModel):
    session_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 2000:
            raise ValueError("Message too long (max 2000 characters)")
        return v


class PackageOut(BaseModel):
    description: str
    weight_kg: float
    declared_value: float


class ShipmentOut(BaseModel):
    id: str
    tracking_number: str
    status: str
    carrier: str
    origin: str
    destination: str
    estimated_delivery: str
    last_update: str | None = None
    # Only populated by lookup_shipment_detail; the list lookup omits packages.
    packages: list[PackageOut] | None = None


class ChatResponse(BaseModel):
    message: str
    state: str
    show_code_modal: bool = False
    is_escalated: bool = False
    escalation_script: list[str] | None = None
    shipments: list[ShipmentOut] | None = None


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(db: AsyncSession = Depends(get_db)):
    # Create DB record first to get the ID
    db_session = ChatSession(
        id=str(uuid.uuid4()),
        state=DBSessionState.anonymous,
        transcript=[],
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)

    # Create in-memory session linked to DB record
    in_mem_session = await session_store.create(chat_session_db_id=db_session.id)
    # The client uses the in-memory session_id (not the DB id)
    return CreateSessionResponse(
        session_id=in_mem_session.session_id,
        state=in_mem_session.state.value,
    )


@router.post("/chat", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Load in-memory session (authoritative for state)
    session = await session_store.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Run the tool loop
    result = await run_tool_loop(
        session=session,
        user_message=request.message,
        db=db,
    )

    # Persist transcript to DB
    if session.chat_session_db_id:
        db_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session.chat_session_db_id)
        )
        db_chat_session = db_result.scalar_one_or_none()
        if db_chat_session:
            now = datetime.now(timezone.utc).isoformat()
            transcript = list(db_chat_session.transcript)
            transcript.append({
                "role": "user",
                "content": request.message,
                "timestamp": now,
            })
            transcript.append({
                "role": "assistant",
                "content": result["message"],
                "timestamp": now,
            })
            # Sync state to DB
            db_chat_session.transcript = transcript
            db_chat_session.state = DBSessionState(session.state.value)
            if session.state == SessionState.VERIFIED and session.verified_customer_id:
                db_chat_session.customer_id = session.verified_customer_id
            await db.commit()

    # Save updated session
    await session_store.save(session)

    return ChatResponse(
        message=result["message"],
        state=session.state.value,
        show_code_modal=result.get("show_code_modal", False),
        is_escalated=result.get("is_escalated", False),
        escalation_script=result.get("escalation_script"),
        shipments=result.get("shipments"),
    )
