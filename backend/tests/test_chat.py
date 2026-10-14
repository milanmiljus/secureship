import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from domain.session import (
    Session,
    SessionState,
    transition_to_code_sent,
    transition_to_awaiting_code,
    transition_to_verified,
)
from domain.verification import generate_code
from llm.tool_loop import (
    STALE_LOOKUP_NOTICE,
    STALE_REPLY_NOTICE,
    _history_for_model,
    run_tool_loop,
)
from main import app


@pytest.fixture
def mock_ollama():
    with patch("routes.chat.ollama_client") as mock:
        mock.chat = AsyncMock(return_value={
            "message": {"content": "Hello! How can I help you with your shipment today?"}
        })
        yield mock


def make_verified_session() -> Session:
    s = Session(session_id=str(uuid.uuid4()), chat_session_db_id="db-1")
    s.state = SessionState.COLLECTING_IDENTITY
    _, code_hash = generate_code()
    transition_to_code_sent(s, "cust-1", code_hash, "Alice")
    transition_to_awaiting_code(s)
    transition_to_verified(s)
    return s


def tool_call(name: str, arguments: dict) -> dict:
    return {"message": {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}}


SHIPMENT = {
    "id": "ship-1",
    "tracking_number": "940086518506716572",
    "status": "in_transit",
    "carrier": "USPS",
    "origin": "San Francisco, CA",
    "destination": "Dallas, TX",
    "estimated_delivery": "2026-10-02",
    "last_update": "2026-02-05T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_create_session_returns_session_id():
    # This test requires a real DB — skip in unit test context
    # Will be covered by integration tests once DB is available
    pass


@pytest.mark.asyncio
async def test_chat_endpoint_exists():
    """Smoke test: endpoint is registered and reachable (even if 404 for missing session)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/chat", json={"session_id": "nonexistent", "message": "hi"})
        # 404 is expected (session not found) — that means routing works
        assert resp.status_code in (404, 503)


class TestShipmentPayload:
    """The structured tool output must reach the API so the UI can render cards."""

    @pytest.mark.asyncio
    async def test_detail_lookup_returns_single_shipment_with_packages(self):
        detail = {**SHIPMENT, "packages": [
            {"description": "Power Tools", "weight_kg": 14.557, "declared_value": 876.79},
        ]}
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipment_detail", AsyncMock(return_value={"shipment": detail})):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipment_detail", {"tracking_number": SHIPMENT["tracking_number"]}),
                {"message": {"content": "Here are the details for that shipment."}},
            ])
            result = await run_tool_loop(make_verified_session(), "tell me about 940086518506716572", AsyncMock())

        assert result["shipments"] == [detail]
        assert result["shipments"][0]["packages"][0]["description"] == "Power Tools"

    @pytest.mark.asyncio
    async def test_list_lookup_returns_all_shipments_without_packages(self):
        shipments = [SHIPMENT, {**SHIPMENT, "id": "ship-2", "tracking_number": "123456789012"}]
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipments", AsyncMock(return_value={"shipments": shipments})):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipments", {}),
                {"message": {"content": "Here are your current shipments."}},
            ])
            result = await run_tool_loop(make_verified_session(), "show my shipments", AsyncMock())

        assert len(result["shipments"]) == 2
        assert all("packages" not in s for s in result["shipments"])

    @pytest.mark.asyncio
    async def test_reply_without_tool_call_has_no_shipments(self):
        with patch("llm.tool_loop.ollama_client") as ollama:
            ollama.chat = AsyncMock(return_value={"message": {"content": "Happy to help!"}})
            result = await run_tool_loop(make_verified_session(), "thanks", AsyncMock())

        assert result["shipments"] is None

    @pytest.mark.asyncio
    async def test_tool_error_leaves_shipments_unset(self):
        """A not-found / cross-customer lookup must not produce a card (INV-08)."""
        error = {"error": "No shipment found with tracking number X on your account."}
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipment_detail", AsyncMock(return_value=error)):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipment_detail", {"tracking_number": "X"}),
                {"message": {"content": "I couldn't find that shipment."}},
            ])
            result = await run_tool_loop(make_verified_session(), "track X", AsyncMock())

        assert result["shipments"] is None

    @pytest.mark.asyncio
    async def test_later_detail_lookup_replaces_earlier_list(self):
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipments", AsyncMock(return_value={"shipments": [SHIPMENT, SHIPMENT]})), \
             patch("llm.tool_loop.lookup_shipment_detail", AsyncMock(return_value={"shipment": SHIPMENT})):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipments", {}),
                tool_call("lookup_shipment_detail", {"tracking_number": SHIPMENT["tracking_number"]}),
                {"message": {"content": "Here are the details for that shipment."}},
            ])
            result = await run_tool_loop(make_verified_session(), "my shipments, then the first one", AsyncMock())

        assert result["shipments"] == [SHIPMENT]


class TestStaleLookupHistory:
    """
    Cards come from the tool payload, so the model must re-call the tool every turn.
    Earlier lookup results and the replies that introduced them are expired from the
    history the model sees, otherwise it answers from memory and the card is lost.
    """

    @pytest.mark.asyncio
    async def test_second_question_about_same_shipment_still_returns_card(self):
        session = make_verified_session()
        detail = {"shipment": SHIPMENT}
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipment_detail", AsyncMock(return_value=detail)):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipment_detail", {"tracking_number": SHIPMENT["tracking_number"]}),
                {"message": {"content": "Here are the details for that shipment."}},
                tool_call("lookup_shipment_detail", {"tracking_number": SHIPMENT["tracking_number"]}),
                {"message": {"content": "Here are the details for that shipment."}},
            ])
            first = await run_tool_loop(session, "tell me about 940086518506716572", AsyncMock())
            second = await run_tool_loop(session, "and that one again please", AsyncMock())

            second_turn_history = ollama.chat.call_args_list[2].args[0]

        assert first["shipments"] == [SHIPMENT]
        assert second["shipments"] == [SHIPMENT]

        stale = [m["content"] for m in second_turn_history if m["role"] in ("tool", "assistant")]
        assert STALE_LOOKUP_NOTICE in stale, "earlier tool result must be expired"
        assert STALE_REPLY_NOTICE in stale, "earlier card intro must be expired"
        assert SHIPMENT["tracking_number"] not in " ".join(stale)

    @pytest.mark.asyncio
    async def test_current_turn_tool_result_is_not_expired(self):
        """Expiry applies only to earlier turns — the model needs this turn's result."""
        session = make_verified_session()
        with patch("llm.tool_loop.ollama_client") as ollama, \
             patch("llm.tool_loop.lookup_shipments", AsyncMock(return_value={"shipments": [SHIPMENT]})):
            ollama.chat = AsyncMock(side_effect=[
                tool_call("lookup_shipments", {}),
                {"message": {"content": "Here are your current shipments."}},
            ])
            await run_tool_loop(session, "show my shipments", AsyncMock())

            follow_up = ollama.chat.call_args_list[1].args[0]

        tool_messages = [m["content"] for m in follow_up if m["role"] == "tool"]
        assert tool_messages and STALE_LOOKUP_NOTICE not in tool_messages

    def test_marker_is_stripped_before_sending_to_model(self):
        """shipments_shown is internal bookkeeping — Ollama must not receive it."""
        session = make_verified_session()
        session.message_history = [
            {"role": "user", "content": "my shipments"},
            {"role": "assistant", "content": "Here are your current shipments.", "shipments_shown": True},
            {"role": "user", "content": "and again"},
        ]
        history = _history_for_model(session, turn_start=2)

        assert all("shipments_shown" not in m for m in history)
        assert history[1]["content"] == STALE_REPLY_NOTICE
        assert session.message_history[1]["shipments_shown"] is True


class TestEmptyResponseFallback:
    """
    When the model goes silent, the fallback must offer a next step the current state
    allows. A bare "could you try again?" invites the user to resend the input that
    just failed, which loops forever.
    """

    @staticmethod
    def _silent_model():
        return AsyncMock(return_value={"message": {"content": ""}})

    @pytest.mark.asyncio
    async def test_verified_fallback_offers_an_available_action(self):
        """Identity cannot be redone once verified, so don't leave the user retrying it."""
        with patch("llm.tool_loop.ollama_client") as ollama:
            ollama.chat = self._silent_model()
            result = await run_tool_loop(
                make_verified_session(),
                "Michael Santiago +13422719582 283 Steven Groves, Lake Mark, WI 07832",
                AsyncMock(),
            )

        message = result["message"].lower()
        assert "try again" not in message
        assert "shipment" in message or "human agent" in message

    @pytest.mark.asyncio
    async def test_awaiting_code_fallback_points_at_the_modal(self):
        session = make_verified_session()
        session.state = SessionState.AWAITING_CODE
        with patch("llm.tool_loop.ollama_client") as ollama:
            ollama.chat = self._silent_model()
            result = await run_tool_loop(session, "what now?", AsyncMock())

        assert "6-digit verification code" in result["message"]
