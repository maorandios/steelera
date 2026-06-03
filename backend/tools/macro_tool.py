"""OpenAI strict tool: apply_macro_action for array/copy/delete on existing members."""

DIMENSION_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "number"},
        "unit": {
            "type": "string",
            "enum": ["m", "mm", "ft", "in", "auto"],
        },
    },
    "required": ["value", "unit"],
    "additionalProperties": False,
}

APPLY_MACRO_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "apply_macro_action",
        "description": (
            "Duplicate (array) or delete an existing member. Use for copy, duplicate, "
            "multiply, array, or delete requests — especially when the user refers to "
            "'this', 'it', or a selected element. Do NOT use add_structural_element for "
            "these operations."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "target_element_id": {
                    "type": "string",
                    "description": "Id of the member to act on (from CURRENT MODEL).",
                },
                "action_type": {
                    "type": "string",
                    "enum": ["ARRAY", "DELETE"],
                },
                "count": {
                    "type": ["integer", "null"],
                    "description": "ARRAY only: number of copies to create (excludes original).",
                },
                "spacing": {
                    "anyOf": [DIMENSION_SCHEMA, {"type": "null"}],
                    "description": "ARRAY only: center-to-center or step spacing between copies.",
                },
                "axis": {
                    "type": ["string", "null"],
                    "enum": ["X", "Y", "Z", None],
                    "description": (
                        "ARRAY only: world-axis offset direction. "
                        "Right = X, up = Y, forward = Z."
                    ),
                },
            },
            "required": [
                "target_element_id",
                "action_type",
                "count",
                "spacing",
                "axis",
            ],
            "additionalProperties": False,
        },
    },
}
