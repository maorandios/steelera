"""OpenAI strict function schema for universal structural generation."""

ELEMENT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "shape_type": {
            "type": "string",
            "enum": ["I-beam", "C-channel", "Box", "Pipe"],
            "description": "Steel section profile",
        },
        "height": {
            "type": "number",
            "description": "Section height in meters",
        },
        "width": {
            "type": "number",
            "description": "Section width or outer diameter in meters",
        },
        "thickness": {
            "type": "number",
            "description": "Wall, web, or flange thickness in meters",
        },
        "length": {
            "type": "number",
            "description": "Member length along local X in meters",
        },
        "position": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "World X in meters"},
                "y": {"type": "number", "description": "World Y in meters"},
                "z": {"type": "number", "description": "World Z in meters"},
            },
            "required": ["x", "y", "z"],
            "additionalProperties": False,
        },
        "axis": {
            "type": "string",
            "enum": ["x", "y", "z"],
            "description": "World axis along which member length runs",
        },
    },
    "required": [
        "shape_type",
        "height",
        "width",
        "thickness",
        "length",
        "position",
        "axis",
    ],
    "additionalProperties": False,
}

GENERATE_STRUCTURAL_ELEMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_structural_elements",
        "description": (
            "Generate or replace the 3D structural model from a list of "
            "parametric steel members. All dimensions in meters."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "elements": {
                    "type": "array",
                    "description": "Structural members to place in the model",
                    "items": ELEMENT_ITEM_SCHEMA,
                },
            },
            "required": ["elements"],
            "additionalProperties": False,
        },
    },
}

STRUCTURAL_TOOLS = [GENERATE_STRUCTURAL_ELEMENTS_TOOL]
