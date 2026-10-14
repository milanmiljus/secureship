import logging
from domain.session import (
    Session,
    SessionState,
    transition_to_verified,
    transition_to_collecting_after_failure,
)
from domain.verification import verify_code, is_code_expired, is_attempts_exceeded

logger = logging.getLogger(__name__)


def check_verification_code(session: Session, submitted_code: str) -> dict:
    """
    Validate a submitted verification code.

    SECURITY: This is the ONLY function that can transition a session to VERIFIED.
    It is called exclusively from POST /verify-code, NOT from the chat endpoint.
    The LLM has no access to this function.

    Returns a result dict with verified=True/False and appropriate messaging.
    """
    if session.state != SessionState.AWAITING_CODE:
        logger.warning(
            "check_verification_code called in wrong state: %s (session=%s)",
            session.state,
            session.session_id,
        )
        return {"verified": False, "message": "No verification is in progress.", "attempts_remaining": None}

    if session.verification_code_hash is None or session.code_sent_at is None:
        return {"verified": False, "message": "Verification code not found. Please restart.", "attempts_remaining": None}

    # Check expiry BEFORE incrementing attempt count
    if is_code_expired(session.code_sent_at):
        logger.info("Verification code expired (session=%s)", session.session_id)
        transition_to_collecting_after_failure(session)
        return {
            "verified": False,
            "message": "Your verification code has expired. Let's start over — please provide your details again.",
            "attempts_remaining": None,
            "reset": True,
        }

    # Increment attempt count
    session.attempt_count += 1

    if not verify_code(submitted_code, session.verification_code_hash):
        logger.info(
            "Wrong verification code (attempt=%d, session=%s)",
            session.attempt_count,
            session.session_id,
        )
        if is_attempts_exceeded(session.attempt_count):
            transition_to_collecting_after_failure(session)
            return {
                "verified": False,
                "message": "Too many incorrect attempts. Please provide your identity details again to get a new code.",
                "attempts_remaining": 0,
                "reset": True,
            }
        remaining = 3 - session.attempt_count  # MAX_CODE_ATTEMPTS - attempt_count
        return {
            "verified": False,
            "message": f"That code is incorrect. You have {remaining} attempt(s) remaining.",
            "attempts_remaining": remaining,
        }

    # SECURITY: Correct code — transition to VERIFIED
    # verified_customer_id is set from pending_customer_id inside the transition function
    transition_to_verified(session)
    logger.info("Session verified (session=%s)", session.session_id)
    return {
        "verified": True,
        "message": "You're verified! You can now ask about your shipments.",
        "attempts_remaining": None,
    }
