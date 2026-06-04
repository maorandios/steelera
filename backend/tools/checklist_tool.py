"""OpenAI tool: show_component_checklist — interactive shed wizard in chat UI."""

SHOW_COMPONENT_CHECKLIST_TOOL = {
    "type": "function",
    "function": {
        "name": "show_component_checklist",
        "description": (
            "REQUIRED when the user wants to create or start a NEW portal-frame shed "
            "(e.g. 'build me a 10x40 duo-pitch shed'). Opens an in-chat checklist for "
            "secondary steel options. Do NOT call modify_shed_assembly or add_structural_element "
            "for a new shed — use this tool first. Convert dimensions to millimeters "
            "(meters × 1000, feet × 304.8). Extract width × length from phrases like "
            "'10x40' or '10 by 40 m'."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "width_mm": {
                    "type": ["number", "null"],
                    "description": "Total width across X in mm, or null if unknown.",
                },
                "length_mm": {
                    "type": ["number", "null"],
                    "description": "Total length along Z in mm, or null if unknown.",
                },
                "height_mm": {
                    "type": ["number", "null"],
                    "description": "Eave height in mm, or null for default 4000.",
                },
                "roof_style": {
                    "type": ["string", "null"],
                    "description": 'duo_pitch, mono_pitch, flat, or null.',
                },
                "roof_pitch_deg": {
                    "type": ["number", "null"],
                    "description": "Roof pitch degrees, or null for default 10.",
                },
                "x_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Optional comma-separated X bay widths in mm, e.g. "10000". '
                        "Null = single bay equal to width."
                    ),
                },
                "z_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Optional comma-separated Z frame bays in mm, e.g. "5000, 5000". '
                        "Null = 5000 mm bays along length."
                    ),
                },
            },
            "required": [
                "width_mm",
                "length_mm",
                "height_mm",
                "roof_style",
                "roof_pitch_deg",
                "x_spans",
                "z_spans",
            ],
            "additionalProperties": False,
        },
    },
}
