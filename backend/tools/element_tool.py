"""OpenAI chat tools — parametric shed config + macro actions."""

from tools.macro_tool import APPLY_MACRO_ACTION_TOOL
from tools.spatial_grid_tool import SUBMIT_STRUCTURAL_GRID_LAYOUT_TOOL
from tools.structural_design_tool import SUBMIT_STRUCTURAL_DESIGN_TOOL

CHAT_TOOLS = [
    SUBMIT_STRUCTURAL_DESIGN_TOOL,
    SUBMIT_STRUCTURAL_GRID_LAYOUT_TOOL,
    APPLY_MACRO_ACTION_TOOL,
]

ELEMENT_TOOLS = CHAT_TOOLS
