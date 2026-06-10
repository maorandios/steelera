"""Non-destructive chat tools — clarify intent or request viewport picking."""

ASK_CLARIFICATION_TOOL = {
    "type": "function",
    "function": {
        "name": "ask_clarification",
        "description": (
            "Ask ONE short clarifying question with 2–4 tap options. "
            "Use when scope or intent is unclear. Never changes the model."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "One short question (max ~15 words).",
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                        },
                        "required": ["label", "value"],
                    },
                    "minItems": 2,
                    "maxItems": 4,
                },
            },
            "required": ["question", "options"],
        },
    },
}

REQUEST_VIEWPORT_NODE_PICK_TOOL = {
    "type": "function",
    "function": {
        "name": "request_viewport_node_pick",
        "description": (
            "Ask the user to click connection nodes on the 3D model to place "
            "custom bracing. Use after intent is clear (single brace vs X-brace)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["single_brace", "full_x"],
                },
                "profile": {
                    "type": "string",
                    "description": "Optional section e.g. L70x70x7",
                },
                "instruction": {
                    "type": "string",
                    "description": "Short instruction shown in chat.",
                },
            },
            "required": ["intent", "instruction"],
        },
    },
}

REQUEST_VIEWPORT_GRID_PICK_TOOL = {
    "type": "function",
    "function": {
        "name": "request_viewport_grid_pick",
        "description": (
            "Ask the user to click a numbered frame line on the 3D model to "
            "insert a new portal frame. Use when adding a frame at a specific bay."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Short instruction shown in chat.",
                },
            },
            "required": ["instruction"],
        },
    },
}

CONSULTATION_TOOLS = [
    ASK_CLARIFICATION_TOOL,
    REQUEST_VIEWPORT_NODE_PICK_TOOL,
    REQUEST_VIEWPORT_GRID_PICK_TOOL,
]
