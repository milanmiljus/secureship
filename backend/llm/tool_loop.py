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
        }

    SECURITY: Tools are dispatched through is_tool_allowed() before execution.
    The model cannot execute a tool that is not permitted in the current state.
    """
    session.message_history.append({"role": "user", "content": user_message})

    show_code_modal = False
    is_escalated = False
    escalation_script = None

    for iteration in range(settings.MAX_TOOL_ITERATIONS):
        allowed_tools = get_allowed_tool_definitions(session.state)
        recent_history = session.message_history[-settings.LLM_MAX_HISTORY:]
        messages = [
            {"role": "system", "content": build_system_prompt(session.state.value, session.collected_fields)},
            *recent_history,
        ]

        try:
            response = await ollama_client.chat(messages, tools=allowed_tools)
        except Exception as e:
            logger.error(
                "Ollama error (iter=%d): [%s] %r",
                iteration, type(e).__name__, str(e),
                exc_info=True,
            )
            final_message = "I'm having trouble connecting to the AI service. Please try again."
            session.message_history.append({"role": "assistant", "content": final_message})
            return {
                "message": final_message,
                "show_code_modal": show_code_modal,
                "is_escalated": is_escalated,
                "escalation_script": escalation_script,
            }

        response_message = response.get("message", {})
        tool_calls = response_message.get("tool_calls") or []
        content = (response_message.get("content") or "").strip()

        # No tool calls and has content → final text response
        if not tool_calls and content:
            session.message_history.append({"role": "assistant", "content": content})
            return {
                "message": content,
                "show_code_modal": show_code_modal,
                "is_escalated": is_escalated,
                "escalation_script": escalation_script,
            }

        # No tool calls and no content → empty response
        if not tool_calls and not content:
            fallback = "I'm sorry, could you please rephrase that?"
            session.message_history.append({"role": "assistant", "content": fallback})
            return {
                "message": fallback,
                "show_code_modal": show_code_modal,
                "is_escalated": is_escalated,
                "escalation_script": escalation_script,
            }

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
                    "content": f"Tool '{tool_name}' is not available in the current state.",
                })
                continue

            result = await _execute_tool(tool_name, args, session, db)

            if tool_name == "verify_identity" and result.get("show_modal"):
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

            tool_results.append({"role": "tool", "content": json.dumps(result)})

        # If escalation triggered, return immediately
        if final_message_override is not None:
            session.message_history.append({"role": "assistant", "content": final_message_override})
            return {
                "message": final_message_override,
                "show_code_modal": show_code_modal,
                "is_escalated": is_escalated,
                "escalation_script": escalation_script,
            }

        # If model also returned content alongside tool_calls, use it as the response
        # (some models do this instead of making a separate text-only call)
        if content:
            session.message_history.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for tr in tool_results:
                session.message_history.append(tr)
            session.message_history.append({"role": "assistant", "content": content})
            return {
                "message": content,
                "show_code_modal": show_code_modal,
                "is_escalated": is_escalated,
                "escalation_script": escalation_script,
            }

        # Append tool exchange to history and loop
        session.message_history.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })
        for tr in tool_results:
            session.message_history.append(tr)

    # Max iterations reached
    logger.warning("Max tool iterations reached (session=%s)", session.session_id)
    fallback = "I'm having difficulty with your request. Please try rephrasing or contact support."
    session.message_history.append({"role": "assistant", "content": fallback})
    return {
        "message": fallback,
        "show_code_modal": show_code_modal,
        "is_escalated": is_escalated,
        "escalation_script": escalation_script,
    }


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
