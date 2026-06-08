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
            "description": (
                "EN catalog designation (e.g. IPE300, HEA200, UB457x191x67, "
                "RHS120x80x5, CHS168.3x5, L100x100x10). Validated server-side."
            ),
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
                            "enum": [
                                "pratt",
                                "howe",
                                "warren",
                                "fink",
                                "king_post",
                                "queen_post",
                                "scissor",
                                "none",
                            ],
                            "description": (
                                "Truss web pattern (used when use_truss=true). "
                                "pratt/howe/warren auto-panel for any span; "
                                "fink/king_post/queen_post/scissor suit symmetric "
                                "duo-pitch gables. 'none' = solid rafters."
                            ),
                        },
                        "x_bracing": {
                            "type": "boolean",
                            "description": "Cross (X) bracing on the LONG side walls (per bay).",
                        },
                        "gable_bracing": {
                            "type": "boolean",
                            "description": "Cross (X) bracing on the two GABLE END walls.",
                        },
                        "roof_bracing": {
                            "type": "boolean",
                            "description": "Cross (X) bracing in the ROOF planes (end bays).",
                        },
                        "sag_rods": {
                            "type": "boolean",
                            "description": "Add anti-sag tension rods between purlins.",
                        },
                        "haunches": {
                            "type": "boolean",
                            "description": (
                                "Tapered eave (knee) + apex haunches on RAFTER (portal) "
                                "frames. Standard for portal sheds; ignored on truss frames."
                            ),
                        },
                        "fly_braces": {
                            "type": "boolean",
                            "description": (
                                "Small fly/flange braces restraining the rafter inner flange "
                                "(purlin stays). Detail-level lateral restraint."
                            ),
                        },
                        "base_plates": {
                            "type": "boolean",
                            "description": "Steel base plates under every column / gable-post foot.",
                        },
                        "bottom_chord_restraint": {
                            "type": "boolean",
                            "description": (
                                "Longitudinal runners restraining truss bottom chords between "
                                "frames (only meaningful with trusses)."
                            ),
                        },
                        "generate_purlins": {
                            "type": "boolean",
                            "description": "Longitudinal roof purlins seated on rafters/truss top chord.",
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
                        "column_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Column section, e.g. HEA200 or SHS300x300x10. "
                                "null = default HEA200."
                            ),
                        },
                        "bracing_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Bracing angle, e.g. L50x50 or L100x100x10. "
                                "null = default L50x50."
                            ),
                        },
                        "purlin_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Purlin section, e.g. C200x2.0 or Z200x2.0. "
                                "null = default C150x2."
                            ),
                        },
                        "girt_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Girt section, e.g. C150x2.0 or Z150x2.0. "
                                "null = default C150x2."
                            ),
                        },
                        "sag_rod_profile": {
                            "type": ["string", "null"],
                            "description": "Sag/tie rod, e.g. ROD12 or ROD16. null = default ROD12.",
                        },
                        "base_plate_profile": {
                            "type": ["string", "null"],
                            "description": "Base plate thickness, e.g. PL12 or PL20. null = default PL20.",
                        },
                        "truss_chord_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Truss top + bottom chord section, e.g. SHS120x120x6 or IPE200. "
                                "null = default IPE200."
                            ),
                        },
                        "truss_web_profile": {
                            "type": ["string", "null"],
                            "description": (
                                "Truss web diagonal section, e.g. L60x60x6 or L50x50. "
                                "null = default L50x50."
                            ),
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
                        "gable_bracing",
                        "roof_bracing",
                        "sag_rods",
                        "haunches",
                        "fly_braces",
                        "base_plates",
                        "bottom_chord_restraint",
                        "generate_purlins",
                        "generate_wall_girts",
                        "generate_tie_beams",
                        "purlin_spacing_mm",
                        "girt_spacing_mm",
                        "column_profile",
                        "bracing_profile",
                        "purlin_profile",
                        "girt_profile",
                        "sag_rod_profile",
                        "base_plate_profile",
                        "truss_chord_profile",
                        "truss_web_profile",
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
