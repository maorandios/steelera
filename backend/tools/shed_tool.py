"""OpenAI strict tool: modify_shed_assembly for portal-frame shed resizing."""

MODIFY_SHED_ASSEMBLY_TOOL = {
    "type": "function",
    "function": {
        "name": "modify_shed_assembly",
        "description": (
            "REQUIRED whenever the user requests a geometric or structural change to an "
            "existing portal-frame shed (assembly shed_1). Internally regenerates the full "
            "macro (same as generate_shed_macro). You MUST call this tool — never claim "
            "the shed changed without a successful tool result. "
            "Read ACTIVE SHED ASSEMBLY in the system prompt for current x_spans and z_spans. "
            "Pass the complete updated comma-separated span strings when bays change. "
            "Use null for every parameter that stays unchanged."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "x_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Full bay widths across X in mm, comma-separated. Example: '
                        '"3000, 7000, 10000, 5000". To add one X bay, copy current x_spans '
                        "from ACTIVE SHED ASSEMBLY and append the new bay width."
                    ),
                },
                "z_spans": {
                    "type": ["string", "null"],
                    "description": (
                        'Full portal-frame bays along +Z in mm, comma-separated. Example: '
                        '"5000, 5000, 5000". User "add a bay to the right" (+Z): take current '
                        "z_spans and append one bay (e.g. 5000) → "
                        '"5000, 5000, 5000, 5000".'
                    ),
                },
                "height": {
                    "type": ["number", "null"],
                    "description": "Eave / outer column height in mm.",
                },
                "roof_pitch_deg": {
                    "type": ["number", "null"],
                    "description": (
                        "Roof pitch in degrees (0–89). Example: user asks 15° → roof_pitch_deg: 15."
                    ),
                },
                "roof_style": {
                    "type": ["string", "null"],
                    "description": (
                        'Roof form: "duo_pitch", "mono_pitch", or "flat". '
                        'Example: "mono pitch" → roof_style: "mono_pitch".'
                    ),
                },
                "use_truss": {
                    "type": ["boolean", "null"],
                    "description": "Use roof trusses instead of solid IPE rafters.",
                },
                "use_bracing": {
                    "type": ["boolean", "null"],
                    "description": "Add wall and roof X-bracing in end Z bays.",
                },
                "use_sag_rods": {
                    "type": ["boolean", "null"],
                    "description": "Add sag rods between neighboring purlins and girts.",
                },
                "generate_wall_girts": {
                    "type": ["boolean", "null"],
                    "description": "Generate perimeter wall girts.",
                },
                "generate_tie_beams": {
                    "type": ["boolean", "null"],
                    "description": "Generate longitudinal eave and ridge tie beams.",
                },
                "girt_spacing_mm": {
                    "type": ["number", "null"],
                    "description": "Vertical spacing of wall girts in mm.",
                },
            },
            "required": [
                "x_spans",
                "z_spans",
                "height",
                "roof_pitch_deg",
                "roof_style",
                "use_truss",
                "use_bracing",
                "use_sag_rods",
                "generate_wall_girts",
                "generate_tie_beams",
                "girt_spacing_mm",
            ],
            "additionalProperties": False,
        },
    },
}
