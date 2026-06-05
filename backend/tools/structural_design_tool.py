"""OpenAI tool: submit_structural_design — grid + universal structural operations."""

_ELEMENT_TYPES = [
    "column", "rafter", "truss_chord", "truss_web", "purlin",
    "wall_girt", "tie_beam", "bracing", "x_brace", "sag_rod",
]
_PROFILES = ["HEA200", "IPE200", "IPE300", "C150", "L50x50", "ROD12"]

_NODE = {
    "type": "object",
    "properties": {
        "x_axis": {"type": "string", "description": 'X line "A","B",… or "A+1/2".'},
        "z_axis": {"type": "string", "description": 'Z line "1","2",… or "1+1/2".'},
        "elevation": {
            "type": "string",
            "description": "ground|eave|roof|apex|ridge, a custom level name, or eave+1/3.",
        },
    },
    "required": ["x_axis", "z_axis", "elevation"],
}

_DEFINE_LEVEL = {
    "type": "object",
    "description": "Declare a named height level (mm) for any vertical structure.",
    "properties": {
        "kind": {"type": "string", "enum": ["define_level"]},
        "name": {"type": "string"},
        "height_mm": {"type": "number"},
    },
    "required": ["kind", "name", "height_mm"],
}

_PLACE_MEMBER = {
    "type": "object",
    "description": "Place one explicit member between two grid nodes.",
    "properties": {
        "kind": {"type": "string", "enum": ["place_member"]},
        "id": {"type": "string"},
        "element_type": {"type": "string", "enum": _ELEMENT_TYPES},
        "profile": {"type": "string", "enum": _PROFILES},
        "start_node": _NODE,
        "end_node": _NODE,
    },
    "required": ["kind", "id", "element_type", "profile", "start_node", "end_node"],
}

_ARRAY_MEMBER = {
    "type": "object",
    "description": (
        "Repeat a template member across grid lines. x_lines/z_lines replace that "
        "coordinate on BOTH endpoints; [] keeps the template value; [\"*\"] = every line. "
        "Columns: x_lines=[\"*\"], z_lines=[\"*\"]. Rafters: x_lines=[], z_lines=[\"*\"]."
    ),
    "properties": {
        "kind": {"type": "string", "enum": ["array_member"]},
        "id_prefix": {"type": "string"},
        "element_type": {"type": "string", "enum": _ELEMENT_TYPES},
        "profile": {"type": "string", "enum": _PROFILES},
        "start_node": _NODE,
        "end_node": _NODE,
        "x_lines": {"type": "array", "items": {"type": "string"}},
        "z_lines": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "kind", "id_prefix", "element_type", "profile",
        "start_node", "end_node", "x_lines", "z_lines",
    ],
}

_ARRAY_ADJACENT = {
    "type": "object",
    "description": (
        "Connect CONSECUTIVE grid lines along `axis`, repeated at each `at_lines` value "
        "on the other axis. Use for longitudinal beams (tie beams, eave beams, girts, purlins). "
        "Tie beams: axis=\"z\", at_lines=[\"A\",\"B\"], elevations \"eave\"."
    ),
    "properties": {
        "kind": {"type": "string", "enum": ["array_adjacent"]},
        "id_prefix": {"type": "string"},
        "element_type": {"type": "string", "enum": _ELEMENT_TYPES},
        "profile": {"type": "string", "enum": _PROFILES},
        "axis": {"type": "string", "enum": ["x", "z"]},
        "at_lines": {"type": "array", "items": {"type": "string"}},
        "elevation_start": {"type": "string"},
        "elevation_end": {"type": "string"},
    },
    "required": [
        "kind", "id_prefix", "element_type", "profile",
        "axis", "at_lines", "elevation_start", "elevation_end",
    ],
}

SUBMIT_STRUCTURAL_DESIGN_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_structural_design",
        "description": (
            "Submit a structural design as a grid_definition plus an ordered list of "
            "universal operations. Python expands and validates them into a precise 3D "
            "model. You decide ALL engineering; you never compute mm coordinates. Compose "
            "columns/rafters/beams with array_member and array_adjacent; define extra "
            "levels (e.g. mezzanine floors) with define_level."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "assembly_id": {"type": "string"},
                "replace_existing": {"type": "boolean"},
                "grid_definition": {
                    "type": "object",
                    "properties": {
                        "x_spans": {"type": "array", "items": {"type": "number"},
                                    "description": "Bay widths across X (mm)."},
                        "z_spans": {"type": "array", "items": {"type": "number"},
                                    "description": "Frame spacings along Z (mm)."},
                        "height_mm": {"type": "number", "description": "Eave height (mm)."},
                        "roof_pitch_deg": {"type": "number"},
                        "roof_style": {"type": "string",
                                       "enum": ["duo_pitch", "mono_pitch", "flat"]},
                        "mono_high_side": {
                            "type": "string",
                            "enum": ["A", "B"],
                            "description": "For mono_pitch only: which side is the HIGH wall.",
                        },
                    },
                    "required": ["x_spans", "z_spans", "height_mm",
                                 "roof_pitch_deg", "roof_style"],
                },
                "operations": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            _DEFINE_LEVEL,
                            _PLACE_MEMBER,
                            _ARRAY_MEMBER,
                            _ARRAY_ADJACENT,
                        ]
                    },
                },
            },
            "required": ["assembly_id", "replace_existing",
                         "grid_definition", "operations"],
        },
    },
}
