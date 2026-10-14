import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from domain.session import Session, SessionState, set_escalated
from llm.client import ollama_client
from llm.prompts import build_system_prompt
from tools.registry import is_tool_allowed, get_allowed_tool_definitions
from tools.verify_identity import verify_identity
from tools.lookup_shipments import lookup_shipments, lookup_shipment_detail

logger = logging.getLogger(__name__)


ESCALATION_SCRIPT = [
    "Thank you for your patience — I'm switching you to a human agent now.",
    "🔵 *Chat transferred to human support*",
    "Melany has entered the chat.",
    "Hey{name_part}, I'm Melany. I'm all caught up — how can I help you?",
]

LOOKUP_TOOLS = ("lookup_shipments", "lookup_shipment_detail")
STALE_LOOKUP_NOTICE = "[Earlier lookup result expired. Call the tool again to answer.]"
STALE_REPLY_NOTICE = (
    "[Presented shipment results to the user. The data was not retained — "
    "call the tool again to answer any further shipment question.]"
)


def _history_for_model(session: Session, turn_start: int) -> list[dict]:
    """
    Build the history sent to the model, expiring everything from earlier shipment
    lookups: the tool results and the reply that introduced them. The UI renders
    shipments from the tool payload, so a reply the model replays from an earlier turn
    would reach the user with no card attached.
    """
    start = max(0, len(session.message_history) - settings.LLM_MAX_HISTORY)
    history = []
    for index, message in enumerate(session.message_history[start:], start=start):
        message = {k: v for k, v in message.items() if k != "shipments_shown"}
        if index < turn_start:
            if message.get("role") == "tool" and message.get("name") in LOOKUP_TOOLS:
                message["content"] = STALE_LOOKUP_NOTICE
            elif session.message_history[index].get("shipments_shown"):
                message["content"] = STALE_REPLY_NOTICE
        history.append(message)
    return history


async def run_tool_loop(
    session: Session,
    user_message: str,
    db: AsyncSession,
) -> dict:
    """
    Run the LLM + tool-calling loop for a single user turn.

    The model calls tools to gather data, then returns plain text as the final reply.
    respond_to_user is NOT a tool — any plain text content from the model IS the reply.

    Returns:
        {
            "message": str,          # final assistant message to show user
            "show_code_modal": bool, # True when session transitions to AWAITING_CODE
            "is_escalated": bool,    # True when escalation triggered
            "escalation_script": list[str] | None,
            "shipments": list[dict] | None,  # structured payload for the UI to render
        }

    SECURITY: Tools are dispatched through is_tool_allowed() before execution.
    The model cannot execute a tool that is not permitted in the current state.
    """
    session.message_history.append({"role": "user", "content": user_message})
    turn_start = len(session.message_history)

    show_code_modal = False
    is_escalated = False
    escalation_script = None
    shipments = None

    def finish(message: str) -> dict:
        entry = {"role": "assistant", "content": message}
        if shipments is not None:
            entry["shipments_shown"] = True
        session.message_history.append(entry)
        return {
            "message": message,
            "show_code_modal": show_code_modal,
            "is_escalated": is_escalated,
            "escalation_script": escalation_script,
            "shipments": shipments,
        }

    for iteration in range(settings.MAX_TOOL_ITERATIONS):
        allowed_tools = get_allowed_tool_definitions(session.state)
        messages = [
            {"role": "system", "content": build_system_prompt(session.state.value, session.collected_fields)},
            *_history_for_model(session, turn_start),
        ]

        try:
            response = await ollama_client.chat(messages, tools=allowed_tools)
        except Exception as e:
            logger.error(
                "Ollama error (iter=%d): [%s] %r",
                iteration, type(e).__name__, str(e),
                exc_info=True,
            )
            return finish("I'm having trouble connecting to the AI service. Please try again.")

        response_message = response.get("message", {})
        tool_calls = response_message.get("tool_calls") or []
        content = (response_message.get("content") or "").strip()

        # No tool calls and has content → final text response
        if not tool_calls and content:
            return finish(content)

        # No tool calls and no content → retry once with a nudge (without polluting history)
        if not tool_calls and not content:
            if iteration == 0:
                try:
                    nudge_messages = messages + [
                        {"role": "user", "content": "Please respond or call the appropriate tool based on my last message."},
                    ]
                    retry_response = await ollama_client.chat(nudge_messages, tools=allowed_tools)
                    retry_msg = retry_response.get("message", {})
                    tool_calls = retry_msg.get("tool_calls") or []
                    content = (retry_msg.get("content") or "").strip()
                    if not tool_calls and not content:
                        raise ValueError("still empty")
                    # Replace response_message so the rest of the loop processes the retry
                    response_message = retry_msg
                except Exception:
                    # Give a state-aware fallback instead of a generic "rephrase" message.
                    # Each one must offer a next step the current state actually allows —
                    # "try again" just invites the user to repeat the input that failed.
                    if session.state in (SessionState.ANONYMOUS, SessionState.COLLECTING_IDENTITY):
                        fallback = "To help you with your shipments, I'll need to verify your identity first. Could you please provide your first name, last name, address, and phone number?"
                    elif session.state in (SessionState.CODE_SENT, SessionState.AWAITING_CODE):
                        fallback = "Please enter the 6-digit verification code in the box that appeared."
                    elif session.state == SessionState.VERIFIED:
                        fallback = "I can't help with that one. You're already verified, so I can show your shipments or look up one of your tracking numbers — or I can connect you to a human agent."
                    else:
                        fallback = "I'm sorry, I had trouble processing that. Could you try again?"
                    return finish(fallback)
                # Fall through with updated tool_calls / content
                if not tool_calls and content:
                    return finish(content)
            else:
                fallback = "I'm sorry, could you please rephrase that?"
                return finish(fallback)

        # Has tool calls → process them
        tool_results = []
        final_message_override = None  # set by trigger_escalation

        for tool_call in tool_calls:
            function_info = tool_call.get("function", {})
            tool_name = function_info.get("name", "")
            raw_args = function_info.get("arguments", "{}")

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except (json.JSONDecodeError, TypeError):
                logger.warning("Malformed tool args for %s: %s", tool_name, raw_args)
                args = {}

            if not is_tool_allowed(tool_name, session.state):
                logger.warning(
                    "BLOCKED: %s in state %s (session=%s)",
                    tool_name, session.state.value, session.session_id,
                )
                tool_results.append({
                    "role": "tool",
                    "content": (
                        f"Tool '{tool_name}' is not available in the current state. "
                        "Do not call it again — tell the user what you can help with instead."
                    ),
                })
                continue

            result = await _execute_tool(tool_name, args, session, db)

            # Keep the structured payload so the UI can render cards instead of parsing prose.
            # Overwrite rather than accumulate: the latest lookup is what the reply is about.
            if tool_name == "lookup_shipments" and "shipments" in result:
                shipments = result["shipments"]
            elif tool_name == "lookup_shipment_detail" and "shipment" in result:
                shipments = [result["shipment"]]

            if result.get("show_modal"):
                show_code_modal = True
                if session.state == SessionState.CODE_SENT:
                    from domain.session import transition_to_awaiting_code
                    transition_to_awaiting_code(session)

            if tool_name == "trigger_escalation":
                is_escalated = True
                set_escalated(session)
                name_part = f", {session.first_name_if_known}" if session.first_name_if_known else ""
                escalation_script = [s.replace("{name_part}", name_part) for s in ESCALATION_SCRIPT]
                final_message_override = escalation_script[0]

            tool_results.append({"role": "tool", "name": tool_name, "content": json.dumps(result)})

        # If escalation triggered, return immediately
        if final_message_override is not None:
            return finish(final_message_override)

        # Append tool exchange to history and loop.
        # NOTE: even if the model also returned text content alongside the tool calls,
        # we do NOT return early — we continue the loop so the model can call further
        # tools (e.g. verify_identity after collect_identity_fields).  The narration
        # text the model emits here ("Let me verify your identity...") is discarded in
        # favour of the real final message the model produces after all tools complete.
        session.message_history.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls,
        })
        for tr in tool_results:
            session.message_history.append(tr)

    # Max iterations reached
    logger.warning("Max tool iterations reached (session=%s)", session.session_id)
    return finish("I'm having difficulty with your request. Please try rephrasing or contact support.")


async def _execute_tool(
    tool_name: str,
    args: dict,
    session: Session,
    db: AsyncSession,
) -> dict:
    """Dispatch to the correct tool function. Returns a result dict."""
    if tool_name == "collect_identity_fields":
        allowed_fields = {"first_name", "last_name", "address", "phone"}
        updates = {k: v for k, v in args.items() if k in allowed_fields and v}
        session.collected_fields.update(updates)
        if "first_name" in updates:
            session.first_name_if_known = updates["first_name"]
        # Transition to COLLECTING_IDENTITY if still ANONYMOUS
        if session.state == SessionState.ANONYMOUS and updates:
            from domain.session import transition_to_collecting_identity
            transition_to_collecting_identity(session)
        # Auto-trigger verify_identity once all 4 fields are present — don't wait for the model
        required = {"first_name", "last_name", "address", "phone"}
        if required.issubset(session.collected_fields):
            return await verify_identity(
                session=session,
                first_name=session.collected_fields["first_name"],
                last_name=session.collected_fields["last_name"],
                address=session.collected_fields["address"],
                phone=session.collected_fields["phone"],
                db=db,
            )
        return {"stored": list(updates.keys()), "collected_so_far": list(session.collected_fields.keys())}

    elif tool_name == "verify_identity":
        return await verify_identity(
            session=session,
            first_name=args.get("first_name", ""),
            last_name=args.get("last_name", ""),
            address=args.get("address", ""),
            phone=args.get("phone", ""),
            db=db,
        )

    elif tool_name == "lookup_shipments":
        # SECURITY: No customer_id argument accepted — scoped to session only
        return await lookup_shipments(session=session, db=db)

    elif tool_name == "lookup_shipment_detail":
        return await lookup_shipment_detail(
            session=session,
            tracking_number=args.get("tracking_number", ""),
            db=db,
        )

    elif tool_name == "trigger_escalation":
        return {"escalated": True}

    else:
        logger.warning("Unknown tool: %s", tool_name)
        return {"error": f"Unknown tool: {tool_name}"}
