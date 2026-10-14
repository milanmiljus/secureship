import pytest
from domain.session import (
    Session,
    SessionState,
    transition_to_collecting_identity,
    transition_to_code_sent,
    transition_to_awaiting_code,
    transition_to_verified,
)
from domain.verification import generate_code, verify_code, is_code_expired, is_attempts_exceeded
from tools.registry import is_tool_allowed, TOOL_PERMISSIONS
from datetime import datetime, timezone, timedelta
import uuid


def make_session(state=SessionState.ANONYMOUS) -> Session:
    s = Session(session_id=str(uuid.uuid4()), chat_session_db_id="test-db-id")
    s.state = state
    return s


# ── State machine tests ──────────────────────────────────────────────────────

class TestStateMachine:
    def test_anonymous_to_collecting(self):
        s = make_session(SessionState.ANONYMOUS)
        transition_to_collecting_identity(s)
        assert s.state == SessionState.COLLECTING_IDENTITY

    def test_collecting_to_code_sent(self):
        s = make_session(SessionState.COLLECTING_IDENTITY)
        _, code_hash = generate_code()
        transition_to_code_sent(s, "cust-123", code_hash, "Alice")
        assert s.state == SessionState.CODE_SENT
        assert s.pending_customer_id == "cust-123"
        assert s.verified_customer_id is None  # NOT yet verified

    def test_code_sent_to_awaiting(self):
        s = make_session(SessionState.COLLECTING_IDENTITY)
        _, code_hash = generate_code()
        transition_to_code_sent(s, "cust-123", code_hash, "Alice")
        transition_to_awaiting_code(s)
        assert s.state == SessionState.AWAITING_CODE

    def test_verified_sets_customer_id_from_pending(self):
        s = make_session(SessionState.COLLECTING_IDENTITY)
        _, code_hash = generate_code()
        transition_to_code_sent(s, "cust-456", code_hash, "Bob")
        transition_to_awaiting_code(s)
        transition_to_verified(s)
        assert s.state == SessionState.VERIFIED
        # SECURITY: verified_customer_id comes from pending, not from model
        assert s.verified_customer_id == "cust-456"
        assert s.pending_customer_id is None  # cleared after verification

    def test_cannot_jump_to_verified_directly(self):
        """Trying to set state to VERIFIED without going through the transition should fail."""
        s = make_session(SessionState.ANONYMOUS)
        with pytest.raises(AssertionError):
            transition_to_verified(s)  # wrong state

    def test_cannot_verify_from_code_sent(self):
        """Must be in AWAITING_CODE to verify."""
        s = make_session(SessionState.COLLECTING_IDENTITY)
        _, code_hash = generate_code()
        transition_to_code_sent(s, "cust-789", code_hash, "Carol")
        # Still in CODE_SENT — should fail
        with pytest.raises(AssertionError):
            transition_to_verified(s)


# ── Tool permissions tests ───────────────────────────────────────────────────

class TestToolPermissions:
    def test_lookup_shipments_blocked_when_anonymous(self):
        assert not is_tool_allowed("lookup_shipments", SessionState.ANONYMOUS)

    def test_lookup_shipments_blocked_when_collecting_identity(self):
        assert not is_tool_allowed("lookup_shipments", SessionState.COLLECTING_IDENTITY)

    def test_lookup_shipments_blocked_when_awaiting_code(self):
        assert not is_tool_allowed("lookup_shipments", SessionState.AWAITING_CODE)

    def test_lookup_shipments_allowed_when_verified(self):
        assert is_tool_allowed("lookup_shipments", SessionState.VERIFIED)

    def test_verify_identity_blocked_when_anonymous(self):
        assert not is_tool_allowed("verify_identity", SessionState.ANONYMOUS)

    def test_verify_identity_allowed_when_collecting_identity(self):
        assert is_tool_allowed("verify_identity", SessionState.COLLECTING_IDENTITY)

    def test_respond_to_user_blocked_in_all_states(self):
        """respond_to_user is no longer a tool — plain text response is used instead."""
        for state in SessionState:
            assert not is_tool_allowed("respond_to_user", state), f"respond_to_user should not be allowed in state {state}"

    def test_unknown_tool_blocked_in_all_states(self):
        for state in SessionState:
            assert not is_tool_allowed("get_all_customers", state)
            assert not is_tool_allowed("override_verification", state)
            assert not is_tool_allowed("set_verified_true", state)


# ── Verification code tests ──────────────────────────────────────────────────

class TestVerificationCode:
    def test_correct_code_verifies(self):
        plain, code_hash = generate_code()
        assert verify_code(plain, code_hash)

    def test_wrong_code_fails(self):
        _, code_hash = generate_code()
        assert not verify_code("000000", code_hash)

    def test_code_not_expired_within_window(self):
        sent_at = datetime.now(timezone.utc)
        assert not is_code_expired(sent_at)

    def test_code_expired_after_window(self):
        sent_at = datetime.now(timezone.utc) - timedelta(minutes=11)
        assert is_code_expired(sent_at)

    def test_attempts_not_exceeded_at_zero(self):
        assert not is_attempts_exceeded(0)

    def test_attempts_exceeded_at_max(self):
        assert is_attempts_exceeded(3)

    def test_six_digit_code_format(self):
        for _ in range(10):
            plain, _ = generate_code()
            assert len(plain) == 6
            assert plain.isdigit()
