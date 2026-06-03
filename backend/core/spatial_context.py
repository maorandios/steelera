"""
Format existing project elements into a readable summary for GPT-4o-mini.
"""

from schemas.elements import ProjectElementMm


def _fmt_pos(el: ProjectElementMm) -> str:
    p = el.position_mm
    return f"({p['x']:.0f}, {p['y']:.0f}, {p['z']:.0f}) mm"


def _fmt_size(el: ProjectElementMm) -> str:
    s = el.size_mm
    return f"{s['x']:.0f}×{s['y']:.0f}×{s['z']:.0f} mm"


def format_element_line(el: ProjectElementMm) -> str:
    """Single-line description of one built member."""
    parts = [
        f"id={el.id}",
        f"type={el.shape_type}",
        f"axis={el.axis}",
        f"pos_min={_fmt_pos(el)}",
        f"size={_fmt_size(el)}",
        f"length={el.length_mm:.0f}mm",
    ]
    if el.profile_name:
        parts.append(f"profile={el.profile_name}")
    if el.section_mm:
        sec = el.section_mm
        parts.append(f"h={sec.h} b={sec.b} tw={sec.tw} tf={sec.tf}mm")
    top_y = el.nodes.get("top", [0, 0, 0])[1] if el.nodes.get("top") else el.position_mm["y"] + el.size_mm["y"]
    parts.append(f"top_y={top_y:.0f}mm")
    if el.nodes:
        parts.append(f"nodes={el.nodes}")
    return "  • " + ", ".join(parts)


def format_project_context(elements: list[ProjectElementMm]) -> str:
    """
    Human-readable inventory injected into the system prompt.
    Returns empty string when the model is empty.
    """
    if not elements:
        return (
            "CURRENT MODEL: empty — no members placed yet. "
            "Use absolute position coordinates for the first member."
        )

    lines = [
        f"CURRENT MODEL: {len(elements)} member(s) already placed.",
        "Use these ids for anchor_element_id when placing relative to existing steel:",
        "",
    ]
    lines.extend(format_element_line(el) for el in elements)
    lines.extend(
        [
            "",
            "Anchoring rules:",
            "- anchor_element_id = target member id, anchor_point = TOP|BOTTOM|START|END|CENTER",
            "- START = start of member, END = far end (top face at end for horizontal beams)",
            "- CENTER = midpoint along member length (top_center for column on beam center)",
            "- Use anchor_point CENTER when user says 'center' or 'middle' of a beam/member",
            "- Use anchor_point END only when user says 'end' or 'tip' of a beam",
            "- Vertical column (axis y) grows upward (+Y) from its bottom node",
            "- When anchoring, set position to {0,0,0} (ignored); geometry resolves from anchor",
            "- Do NOT rebuild the whole model when adding to existing — append new members only",
        ]
    )
    return "\n".join(lines)
