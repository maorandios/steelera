"""OpenAI tool: submit_structural_layout — AI-computed structural BOM (explicit nodes)."""

_BOM_PROFILE_ENUM = ["HEA200", "IPE200", "IPE300", "C150", "L50x50", "ROD12"]

_BOM_MEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "element_type": {
            "type": "string",
            "enum": [
                "column",
                "rafter",
                "truss_chord",
                "truss_web",
                "purlin",
                "wall_girt",
                "x_brace",
                "sag_rod",
            ],
        },
        "profile": {
            "type": "string",
            "enum": _BOM_PROFILE_ENUM,
        },
        "start_node": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3,
            "description": "Start connection [x, y, z] in mm. Y is vertical.",
        },
        "end_node": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3,
            "description": "End connection [x, y, z] in mm.",
        },
        "rotation_deg": {
            "type": "number",
            "description": "Rotation about vertical (Z euler) for sloped members; 0 if axis-aligned.",
        },
    },
    "required": [
        "element_type",
        "profile",
        "start_node",
        "end_node",
        "rotation_deg",
    ],
    "additionalProperties": False,
}

SUBMIT_STRUCTURAL_LAYOUT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_structural_layout",
        "description": (
            "REQUIRED for any portal-frame shed, structural layout, or multi-member steel "
            "generation. You are the structural engineering engine: compute exact 3D nodes "
            "(mm) for every member and return the complete BOM in `elements`. "
            "The Python backend renders these coordinates verbatim — no macro recalculation. "
            "Include ALL members: columns, rafters/trusses, purlins, girts, bracing, sag rods. "
            "Never claim the model was built without calling this tool with a full array."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assembly_id": {
                    "type": "string",
                    "description": 'Assembly tag, usually "shed_1".',
                },
                "replace_existing": {
                    "type": "boolean",
                    "description": (
                        "True = replace all members in this assembly. "
                        "False = append to the assembly."
                    ),
                },
                "elements": {
                    "type": "array",
                    "description": (
                        "Complete structural BOM. Each object: element_type, profile, "
                        "start_node [x,y,z], end_node [x,y,z], rotation_deg."
                    ),
                    "items": _BOM_MEMBER_SCHEMA,
                },
            },
            "required": ["assembly_id", "replace_existing", "elements"],
            "additionalProperties": False,
        },
    },
}
