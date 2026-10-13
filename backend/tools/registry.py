from domain.session import SessionState

# The only tools available in each state.
# This dict is the single enforcement point — no tool executes unless its name
# appears here for the current session state. Model behavior cannot change this.
TOOL_PERMISSIONS: dict[SessionState, set[str]] = {
    SessionState.ANONYMOUS: {
        "collect_identity_fields",
        "trigger_escalation",
    },
    SessionState.COLLECTING_IDENTITY: {
        "collect_identity_fields",
        "verify_identity",
        "trigger_escalation",
    },
    SessionState.CODE_SENT: {
        "trigger_escalation",
    },
    SessionState.AWAITING_CODE: {
        "trigger_escalation",
    },
    SessionState.VERIFIED: {
        "lookup_shipments",
        "lookup_shipment_detail",
        "trigger_escalation",
    },
    SessionState.ESCALATED_TO_HUMAN: set(),
}


def is_tool_allowed(tool_name: str, state: SessionState) -> bool:
    """Return True only if this tool is permitted in the given session state."""
    return tool_name in TOOL_PERMISSIONS.get(state, set())


# Tool definitions sent to Ollama (OpenAI function-calling format)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "collect_identity_fields",
            "description": (
                "Store identity fields the user has provided so far. "
                "Call this whenever the user provides any of: first name, last name, address, or phone number. "
                "Only include fields the user actually provided in this message."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Customer first name"},
                    "last_name": {"type": "string", "description": "Customer last name"},
                    "address": {"type": "string", "description": "Customer address"},
                    "phone": {"type": "string", "description": "Customer phone number"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_identity",
            "description": (
                "Attempt to verify the customer's identity using all four collected fields. "
                "Only call this when you have first_name, last_name, address, AND phone. "
                "Do not call this with partial information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "address": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["first_name", "last_name", "address", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_shipments",
            "description": (
                "Look up all shipments for the verified customer. "
                "Only available after identity verification is complete. "
                "Takes no arguments — the customer identity is determined by the verified session."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_shipment_detail",
            "description": (
                "Look up details for a specific shipment by tracking number. "
                "Only available after identity verification. "
                "The shipment must belong to the verified customer — other customers' shipments are not accessible."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The tracking number of the shipment",
                    }
                },
                "required": ["tracking_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_escalation",
            "description": (
                "Trigger the human escalation sequence when a user explicitly asks to speak with a human. "
                "This starts a scripted handoff sequence."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def get_allowed_tool_definitions(state: SessionState) -> list[dict]:
    """Return only the tool definitions allowed in the current state."""
    allowed = TOOL_PERMISSIONS.get(state, set())
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in allowed]
