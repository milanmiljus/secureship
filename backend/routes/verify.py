import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from domain.session import SessionState, transition_to_awaiting_code
from services.session_store import session_store
from tools.check_verification_code import check_verification_code

router = APIRouter()
logger = logging.getLogger(__name__)


class VerifyCodeRequest(BaseModel):
    session_id: str
    code: str

    @field_validator("code")
    @classmethod
    def code_must_be_six_digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        return v


class VerifyCodeResponse(BaseModel):
    verified: bool
    message: str
    attempts_remaining: int | None = None
    reset: bool = False


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code_endpoint(request: VerifyCodeRequest):
    session = await session_store.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Ensure we're in the right state for code entry
    if session.state == SessionState.CODE_SENT:
        transition_to_awaiting_code(session)

    if session.state != SessionState.AWAITING_CODE:
        raise HTTPException(
            status_code=410,
            detail="No verification in progress for this session",
        )

    result = check_verification_code(session, request.code)
    await session_store.save(session)

    return VerifyCodeResponse(
        verified=result["verified"],
        message=result["message"],
        attempts_remaining=result.get("attempts_remaining"),
        reset=result.get("reset", False),
    )
