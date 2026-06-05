"""OpenAI tool: submit_structural_grid_layout — grid definition + uniform structural_members."""

_GRID_NODE_SCHEMA = {
    "type": "object",
    "properties": {
        "x_axis": {
            "type": "string",
            "description": 'X line: "A", "B", or "A+2/5" (use + not -) between A and B.',
        },
        "z_axis": {
            "type": "string",
            "description": 'Z line: "1", "2", or "1+1/3" between frames.',
        },
        "elevation": {
            "type": "string",
            "description": "Use only: ground, eave, roof, apex, ridge (not rooftop/top). Optional eave+2/5",
        },
    },
    "required": ["x_axis", "z_axis", "elevation"],
    "additionalProperties": False,
}

_MEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "element_type": {
            "type": "string",
            "enum": [
                "column",
                "rafter",
                "truss_chord",
                "truss_web",
                "purlin",
                "wall_girt",
                "tie_beam",
                "bracing",
                "x_brace",
                "sag_rod",
            ],
        },
        "profile": {
            "type": "string",
            "enum": ["HEA200", "IPE200", "IPE300", "C150", "L50x50", "ROD12"],
        },
        "start_node": _GRID_NODE_SCHEMA,
        "end_node": _GRID_NODE_SCHEMA,
    },
    "required": ["id", "element_type", "profile", "start_node", "end_node"],
    "additionalProperties": False,
}

SUBMIT_STRUCTURAL_GRID_LAYOUT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_structural_grid_layout",
        "description": (
            "Build a complete shed/portal-frame from PARAMETERS. Provide grid_definition "
            "(dimensions + roof + capability toggles) and structural_members: [] (EMPTY). "
            "Python's engine generates every member (columns, rafters/trusses, tie beams, "
            "purlins, wall girts, gable posts, bracing, sag rods) with flawless geometry. "
            "Do NOT hand-author members — leave structural_members empty."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assembly_id": {"type": "string"},
                "replace_existing": {"type": "boolean"},
                "grid_definition": {
                    "type": "object",
                    "properties": {
                        "x_spans": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Bay widths across X (mm); sum = total width.",
                        },
                        "z_spans": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Frame bay spacings along Z (mm); sum = total length.",
                        },
                        "height_mm": {"type": "number", "description": "Eave height (mm)."},
                        "roof_pitch_deg": {"type": "number"},
                        "roof_style": {
                            "type": "string",
                            "enum": ["duo_pitch", "mono_pitch", "flat"],
                        },
                        "mono_high_side": {
                            "type": "string",
                            "enum": ["A", "B"],
                            "description": "Mono-pitch only: which side is tall (A=x0, B=xmax).",
                        },
                        "use_truss": {
                            "type": "boolean",
                            "description": "Replace rafters with trusses on each frame.",
                        },
                        "truss_type": {
                            "type": "string",
                            "enum": ["pratt", "warren", "none"],
                        },
                        "x_bracing": {
                            "type": "boolean",
                            "description": "Add cross (X) wall bracing per bay.",
                        },
                        "sag_rods": {
                            "type": "boolean",
                            "description": "Add anti-sag tension rods between purlins.",
                        },
                        "generate_wall_girts": {"type": "boolean"},
                        "generate_tie_beams": {"type": "boolean"},
                        "purlin_spacing_mm": {
                            "type": "number",
                            "description": "Roof purlin spacing across the slope (default 1200).",
                        },
                        "girt_spacing_mm": {
                            "type": "number",
                            "description": "Wall girt vertical spacing (default 1500).",
                        },
                    },
                    "required": [
                        "x_spans",
                        "z_spans",
                        "height_mm",
                        "roof_pitch_deg",
                        "roof_style",
                        "mono_high_side",
                        "use_truss",
                        "truss_type",
                        "x_bracing",
                        "sag_rods",
                        "generate_wall_girts",
                        "generate_tie_beams",
                        "purlin_spacing_mm",
                        "girt_spacing_mm",
                    ],
                    "additionalProperties": False,
                },
                "structural_members": {
                    "type": "array",
                    "items": _MEMBER_SCHEMA,
                    "description": "Leave EMPTY ([]). Python auto-generates the full shed.",
                },
            },
            "required": [
                "assembly_id",
                "replace_existing",
                "grid_definition",
                "structural_members",
            ],
            "additionalProperties": False,
        },
    },
}
