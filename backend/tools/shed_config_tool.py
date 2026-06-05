"""OpenAI tool: submit_shed_assembly_config — parametric layout (Python computes geometry)."""

_BAY_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "bay_index": {
            "type": "integer",
            "description": "Longitudinal Z-bay index 0..len(z_spans)-1.",
        },
        "use_truss": {"type": "boolean"},
        "truss_type": {
            "type": "string",
            "enum": ["pratt", "warren", "none"],
        },
        "x_bracing_left_wall": {"type": "boolean"},
        "x_bracing_right_wall": {"type": "boolean"},
        "wall_girts": {"type": "boolean"},
        "sag_rods": {"type": "boolean"},
    },
    "required": [
        "bay_index",
        "use_truss",
        "truss_type",
        "x_bracing_left_wall",
        "x_bracing_right_wall",
        "wall_girts",
        "sag_rods",
    ],
    "additionalProperties": False,
}

SUBMIT_SHED_ASSEMBLY_CONFIG_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_shed_assembly_config",
        "description": (
            "Submit the full parametric portal-frame configuration. You are the structural "
            "coordinator: set global_parameters, grid_layout (x_spans, z_spans in mm), and "
            "bays_configuration per longitudinal bay. Do NOT compute absolute 3D coordinates — "
            "the Python engine generates all member nodes. Use replace_existing true for new "
            "builds. Include every bay index 0..n-1 with explicit flags."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assembly_id": {"type": "string"},
                "replace_existing": {"type": "boolean"},
                "global_parameters": {
                    "type": "object",
                    "properties": {
                        "height_mm": {"type": "number"},
                        "roof_pitch_deg": {"type": "number"},
                        "roof_style": {
                            "type": "string",
                            "enum": ["duo_pitch", "mono_pitch", "flat"],
                        },
                    },
                    "required": ["height_mm", "roof_pitch_deg", "roof_style"],
                    "additionalProperties": False,
                },
                "grid_layout": {
                    "type": "object",
                    "properties": {
                        "x_spans": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "z_spans": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                    },
                    "required": ["x_spans", "z_spans"],
                    "additionalProperties": False,
                },
                "bays_configuration": {
                    "type": "array",
                    "items": _BAY_CONFIG_SCHEMA,
                },
                "purlin_spacing_mm": {"type": "number"},
                "girt_spacing_mm": {"type": "number"},
                "generate_tie_beams": {"type": "boolean"},
            },
            "required": [
                "assembly_id",
                "replace_existing",
                "global_parameters",
                "grid_layout",
                "bays_configuration",
                "purlin_spacing_mm",
                "girt_spacing_mm",
                "generate_tie_beams",
            ],
            "additionalProperties": False,
        },
    },
}
