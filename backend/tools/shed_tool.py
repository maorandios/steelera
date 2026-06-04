"""OpenAI strict tool: modify_shed_assembly for portal-frame shed resizing."""

MODIFY_SHED_ASSEMBLY_TOOL = {
    "type": "function",
    "function": {
        "name": "modify_shed_assembly",
        "description": (
            "Use this tool whenever the user asks to modify, resize, change profiles, "
            "or update parameters of the existing shed structure (e.g., 'make the shed higher', "
            "'change X spans', 'increase roof pitch'). "
            "All dimensions are in millimeters unless the user specifies meters "
            "(then convert: meters × 1000). Regenerates the full shed_1 assembly."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "x_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Bay widths across X in mm, comma-separated, e.g. "3000, 7000, 10000, 5000".'
                    ),
                },
                "z_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Portal frame bays along Z in mm, comma-separated, e.g. "5000, 5000, 5000".'
                    ),
                },
                "height": {
                    "type": ["number", "null"],
                    "description": "Eave / outer column height in mm.",
                },
                "roof_pitch_deg": {
                    "type": ["number", "null"],
                    "description": "Roof pitch in degrees (0–89).",
                },
            },
            "required": ["x_spans", "z_spans", "height", "roof_pitch_deg"],
            "additionalProperties": False,
        },
    },
}
