"""OpenAI chat tools — parametric shed config + macro actions."""

from tools.consultation_tools import CONSULTATION_TOOLS
from tools.macro_tool import APPLY_MACRO_ACTION_TOOL
from tools.model_edit_tool import UPDATE_MEMBER_PROFILE_TOOL
from tools.spatial_grid_tool import SUBMIT_STRUCTURAL_GRID_LAYOUT_TOOL

CHAT_TOOLS = [
    *CONSULTATION_TOOLS,
    UPDATE_MEMBER_PROFILE_TOOL,
    SUBMIT_STRUCTURAL_GRID_LAYOUT_TOOL,
    APPLY_MACRO_ACTION_TOOL,
]

ELEMENT_TOOLS = CHAT_TOOLS
