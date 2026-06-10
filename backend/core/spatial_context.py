"""
Format existing project elements into a readable summary for GPT-4o-mini.
Large models use a compact summary to stay within context limits.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from schemas.chat import SelectionContextPayload
from schemas.elements import ProjectElementMm

FULL_DETAIL_ELEMENT_LIMIT = 48
COMPACT_FRAME_MEMBER_LIMIT = 24

_COL_FRAME_RE = re.compile(r"-col-[A-Z]+-(\d+)$")
_RAFTER_FRAME_RE = re.compile(r"-rafter(?:-(?:L|R))?-(\d+)$")
_TRUSS_FRAME_RE = re.compile(r"-truss-(?:TC|BC|web|post)-(\d+)")


def _fmt_pos(el: ProjectElementMm) -> str:
    p = el.position_mm
    return f"({p['x']:.0f}, {p['y']:.0f}, {p['z']:.0f}) mm"


def _fmt_size(el: ProjectElementMm) -> str:
    s = el.size_mm
    return f"{s['x']:.0f}×{s['y']:.0f}×{s['z']:.0f} mm"


def _element_role(el: ProjectElementMm) -> str:
    return str(el.element_type or el.shape_type or "member")


def _frame_z_label(el: ProjectElementMm) -> str | None:
    eid = el.id
    for pattern in (_COL_FRAME_RE, _RAFTER_FRAME_RE, _TRUSS_FRAME_RE):
        m = pattern.search(eid)
        if m:
            return m.group(1)
    if "-col-" in eid:
        parts = eid.split("-")
        if parts and parts[-1].isdigit():
            return parts[-1]
    return None


def format_element_line(el: ProjectElementMm, *, include_nodes: bool = True) -> str:
    """Single-line description of one built member."""
    parts = [
        f"id={el.id}",
        f"type={_element_role(el)}",
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
    top_y = (
        el.nodes.get("top", [0, 0, 0])[1]
        if el.nodes and el.nodes.get("top")
        else el.position_mm["y"] + el.size_mm["y"]
    )
    parts.append(f"top_y={top_y:.0f}mm")
    if include_nodes and el.nodes:
        parts.append(f"nodes={el.nodes}")
    return "  • " + ", ".join(parts)


def _model_bounds_mm(elements: list[ProjectElementMm]) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for el in elements:
        p = el.position_mm
        s = el.size_mm
        xs.extend([p["x"], p["x"] + s["x"]])
        ys.extend([p["y"], p["y"] + s["y"]])
        zs.extend([p["z"], p["z"] + s["z"]])
    if not xs:
        return {}
    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_z": min(zs),
        "max_z": max(zs),
    }


def _profile_summary(elements: list[ProjectElementMm]) -> list[str]:
    by_role: dict[str, set[str]] = defaultdict(set)
    for el in elements:
        if el.profile_name:
            by_role[_element_role(el)].add(el.profile_name)
    lines: list[str] = []
    for role in sorted(by_role):
        profiles = sorted(by_role[role])
        if len(profiles) <= 4:
            lines.append(f"  - {role}: {', '.join(profiles)}")
        else:
            lines.append(
                f"  - {role}: {', '.join(profiles[:3])}, … ({len(profiles)} profiles)"
            )
    return lines


def _type_count_lines(elements: list[ProjectElementMm]) -> list[str]:
    counts = Counter(_element_role(el) for el in elements)
    return [f"  - {role}: {count}" for role, count in counts.most_common()]


def _frame_labels(elements: list[ProjectElementMm]) -> list[str]:
    labels = sorted({z for el in elements if (z := _frame_z_label(el))})
    return labels


def _elements_on_frame(
    elements: list[ProjectElementMm], frame_z: str
) -> list[ProjectElementMm]:
    matched: list[ProjectElementMm] = []
    for el in elements:
        z = _frame_z_label(el)
        if z == frame_z:
            matched.append(el)
            continue
        if f"-{frame_z}-" in el.id or el.id.endswith(f"-{frame_z}"):
            matched.append(el)
    return matched[:COMPACT_FRAME_MEMBER_LIMIT]


def _compact_context(
    elements: list[ProjectElementMm],
    *,
    focus_element_id: str | None = None,
    selection: SelectionContextPayload | None = None,
) -> str:
    lines = [
        f"CURRENT MODEL (compact summary): {len(elements)} members — full member list omitted.",
        "Use submit_structural_grid_layout for layout-wide changes; /api/model for surgical edits.",
        "",
        "Member counts by role:",
        *_type_count_lines(elements),
    ]

    profiles = _profile_summary(elements)
    if profiles:
        lines.extend(["", "Profiles in use:", *profiles])

    bounds = _model_bounds_mm(elements)
    if bounds:
        width = bounds["max_x"] - bounds["min_x"]
        length = bounds["max_z"] - bounds["min_z"]
        height = bounds["max_y"] - bounds["min_y"]
        lines.extend(
            [
                "",
                "Approximate envelope (mm):",
                f"  - width (X): {width:.0f}",
                f"  - length (Z): {length:.0f}",
                f"  - height (Y): {height:.0f}",
            ]
        )

    frames = _frame_labels(elements)
    if frames:
        lines.extend(
            [
                "",
                f"Portal frame lines detected: {len(frames)} "
                f"(labels {frames[0]}–{frames[-1]})",
            ]
        )

    focus_id = focus_element_id or (selection.element_id if selection else None)
    if focus_id:
        focus = next((e for e in elements if e.id == focus_id), None)
        if focus:
            lines.extend(["", "SELECTED MEMBER (full detail):", format_element_line(focus)])
            frame_z = _frame_z_label(focus)
            if frame_z:
                frame_members = _elements_on_frame(elements, frame_z)
                others = [e for e in frame_members if e.id != focus_id]
                if others:
                    lines.append("")
                    lines.append(
                        f"Same frame ({frame_z}) — {len(others)} other member(s) "
                        f"(ids + profiles only):"
                    )
                    for el in others[:COMPACT_FRAME_MEMBER_LIMIT]:
                        prof = el.profile_name or "?"
                        lines.append(f"  • id={el.id}, type={_element_role(el)}, profile={prof}")

    lines.extend(
        [
            "",
            "Anchoring rules (when adding individual members):",
            "- anchor_element_id = target member id, anchor_point = TOP|BOTTOM|START|END|CENTER",
            "- For layout changes on sheds this large, prefer submit_structural_grid_layout.",
        ]
    )
    return "\n".join(lines)


def format_project_context(
    elements: list[ProjectElementMm],
    *,
    focus_element_id: str | None = None,
    selection: SelectionContextPayload | None = None,
) -> str:
    """
    Human-readable inventory injected into the system prompt.
    Returns empty string when the model is empty.
    """
    if not elements:
        return (
            "CURRENT MODEL: empty — no members placed yet. "
            "Use absolute position coordinates for the first member."
        )

    focus_id = focus_element_id or (selection.element_id if selection else None)

    if len(elements) > FULL_DETAIL_ELEMENT_LIMIT:
        return _compact_context(
            elements,
            focus_element_id=focus_id,
            selection=selection,
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
