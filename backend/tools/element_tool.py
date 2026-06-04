"""OpenAI strict tool: add_structural_element with catalog + spatial anchoring."""

from catalog_loader import CATALOG_PROFILE_NAMES

PROFILE_ENUM = ["NONE", *CATALOG_PROFILE_NAMES]
ANCHOR_POINT_ENUM = ["NONE", "TOP", "BOTTOM", "START", "END", "CENTER"]

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

ADD_STRUCTURAL_ELEMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "add_structural_element",
        "description": (
            "Add one structural steel member. Use anchor_element_id + anchor_point "
            "to place relative to an existing member (see CURRENT MODEL in system prompt). "
            "Use profile_name for European catalog sections."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "shape_type": {
                    "type": "string",
                    "enum": ["I-beam", "C-channel", "Box", "Pipe"],
                },
                "length": DIMENSION_SCHEMA,
                "width": DIMENSION_SCHEMA,
                "position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "z": {"type": "number"},
                    },
                    "required": ["x", "y", "z"],
                    "additionalProperties": False,
                },
                "profile_name": {
                    "type": "string",
                    "enum": PROFILE_ENUM,
                },
                "axis": {
                    "type": "string",
                    "enum": ["x", "y", "z"],
                },
                "anchor_element_id": {
                    "type": "string",
                    "description": (
                        "Id of existing element to attach to (from CURRENT MODEL), "
                        "or NONE for absolute position"
                    ),
                },
                "anchor_point": {
                    "type": "string",
                    "enum": ANCHOR_POINT_ENUM,
                    "description": (
                        "Attachment: TOP, BOTTOM, START, END, CENTER (midpoint), or NONE"
                    ),
                },
            },
            "required": [
                "shape_type",
                "length",
                "width",
                "position",
                "profile_name",
                "axis",
                "anchor_element_id",
                "anchor_point",
            ],
            "additionalProperties": False,
        },
    },
}

from tools.checklist_tool import SHOW_COMPONENT_CHECKLIST_TOOL
from tools.macro_tool import APPLY_MACRO_ACTION_TOOL
from tools.shed_tool import MODIFY_SHED_ASSEMBLY_TOOL

ELEMENT_TOOLS = [
    ADD_STRUCTURAL_ELEMENT_TOOL,
    APPLY_MACRO_ACTION_TOOL,
    MODIFY_SHED_ASSEMBLY_TOOL,
    SHOW_COMPONENT_CHECKLIST_TOOL,
]
