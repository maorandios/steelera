"""Deterministic surgical edits on an existing project model."""

from __future__ import annotations

import math
import re
from typing import Iterable, Literal

from catalog_loader import get_profile, has_profile
from core.geometry_engine import macro_member_to_project_element
from core.ground_placement import (
    collect_ground_placement_nodes,
    structural_member_for_column,
)
from core.member_resolver import member_from_grid_nodes
from core.spatial_grid import StructuralGridEngine
from schemas.elements import ProjectElementMm, SectionDimensionsMm
from schemas.model_edit import GridPlacementContext
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralMember

_AXIS_SAFE_RE = re.compile(r"[^A-Za-z0-9]+")

_BRACE_PAIR_RE = re.compile(r"^(?P<prefix>.+)-([ab])$", re.IGNORECASE)

_ENDPOINT_ROUND_MM = 1.0
_MIN_MEMBER_LENGTH_MM = 50.0


def _brace_pair_prefix(element_id: str) -> str | None:
    match = _BRACE_PAIR_RE.match(element_id)
    if not match:
        return None
    return match.group("prefix")


def _brace_pair_ids(element_id: str) -> tuple[str, str] | None:
    prefix = _brace_pair_prefix(element_id)
    if not prefix:
        return None
    return f"{prefix}-a", f"{prefix}-b"


_COL_RE = re.compile(r"^.+-col-[A-Z]+-(?P<z>\d+)$")
_RAFTER_RE = re.compile(r"^.+-rafter(?:-(?:L|R))?-(?P<z>\d+)$")
_TRUSS_RE = re.compile(r"^.+-truss-(?:TC|BC|web|post)-(?P<z>\d+)(?:-|$)")
_HAUNCH_RE = re.compile(r"^.+-haunch-(?P<z>\d+)-")


def _frame_z_from_id(element_id: str) -> str | None:
    for pattern in (_COL_RE, _RAFTER_RE, _TRUSS_RE, _HAUNCH_RE):
        match = pattern.match(element_id)
        if match:
            return match.group("z")
    return None


def _matches_frame(element: ProjectElementMm, frame_z: str) -> bool:
    z = _frame_z_from_id(element.id)
    if z == frame_z:
        return True
    return element.id.endswith(f"-{frame_z}") or f"-{frame_z}-" in element.id


def _is_truss_member(element: ProjectElementMm) -> bool:
    et = element.element_type or ""
    if et in ("truss_chord", "truss_web"):
        return True
    return bool(_TRUSS_RE.match(element.id))


def _bracing_group_key(element: ProjectElementMm) -> str | None:
    if element.element_type not in ("bracing", "x_brace"):
        if "-brace-" not in element.id:
            return None
    et = element.element_type or "bracing"
    if "-brace-roof-" in element.id:
        return "roof_bracing"
    if "-brace-end-" in element.id:
        return "gable_bracing"
    if re.search(r"-brace-[AB]-", element.id, re.IGNORECASE):
        return "wall_bracing"
    return et


def _resolve_target_ids(
    elements: list[ProjectElementMm],
    *,
    reference_element_id: str | None,
    scope: str,
) -> list[str]:
    if not reference_element_id:
        return []
    ref = next((e for e in elements if e.id == reference_element_id), None)
    if ref is None:
        raise ValueError(f"Element not found: {reference_element_id}")

    if scope == "selection":
        return [reference_element_id]

    if scope == "pair":
        pair = _brace_pair_ids(reference_element_id)
        if pair:
            return [eid for eid in pair if any(e.id == eid for e in elements)]
        return [reference_element_id]

    if scope == "group":
        key = _bracing_group_key(ref)
        if not key:
            return [reference_element_id]
        return [
            e.id
            for e in elements
            if _bracing_group_key(e) == key
        ]

    if scope == "element_type":
        et = ref.element_type or "bracing"
        return [e.id for e in elements if (e.element_type or "") == et]

    if scope == "frame":
        frame_z = _frame_z_from_id(reference_element_id)
        if not frame_z:
            return [reference_element_id]
        return [e.id for e in elements if _matches_frame(e, frame_z)]

    if scope == "truss":
        frame_z = _frame_z_from_id(reference_element_id)
        if not frame_z:
            return [reference_element_id]
        return [
            e.id
            for e in elements
            if _matches_frame(e, frame_z) and _is_truss_member(e)
        ]

    return [reference_element_id]


def _apply_profile_to_element(
    element: ProjectElementMm,
    profile: str,
) -> ProjectElementMm:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    cat = get_profile(profile)
    section = SectionDimensionsMm(
        h=float(cat["h"]),
        b=float(cat["b"]),
        tw=float(cat.get("tw") or 0),
        tf=float(cat.get("tf") or 0),
        t=cat.get("t"),
        d=cat.get("d"),
        ro=cat.get("ro"),
        r=cat.get("r"),
        lip=cat.get("lip"),
    )
    shape = str(cat.get("shape", "Angle"))
    shape_map = {
        "Angle": "Angle",
        "I-beam": "I-beam",
        "RHS": "RHS",
        "SHS": "RHS",
        "CHS": "CHS",
        "Pipe": "Pipe",
        "C-channel": "C-channel",
        "Zed": "Zed",
        "Tee": "Tee",
        "Plate": "Plate",
    }
    return element.model_copy(
        update={
            "profile_name": profile,
            "section_source": "catalog",
            "section_mm": section,
            "shape_type": shape_map.get(shape, element.shape_type),
            "depth_mm": section.h,
            "width_mm": section.b,
        }
    )


def update_member_profiles(
    elements: list[ProjectElementMm],
    *,
    profile: str,
    element_ids: Iterable[str] | None = None,
    reference_element_id: str | None = None,
    scope: str = "selection",
) -> tuple[list[ProjectElementMm], list[str]]:
    if element_ids:
        targets = set(element_ids)
    else:
        targets = set(
            _resolve_target_ids(
                elements,
                reference_element_id=reference_element_id,
                scope=scope,
            )
        )
    if not targets:
        raise ValueError("No target members to update")

    changed: list[str] = []
    out: list[ProjectElementMm] = []
    for element in elements:
        if element.id in targets:
            out.append(_apply_profile_to_element(element, profile))
            changed.append(element.id)
        else:
            out.append(element)
    return out, changed


def delete_members(
    elements: list[ProjectElementMm],
    *,
    element_ids: Iterable[str] | None = None,
    reference_element_id: str | None = None,
    scope: str = "selection",
) -> tuple[list[ProjectElementMm], list[str]]:
    if element_ids:
        targets = set(element_ids)
    else:
        targets = set(
            _resolve_target_ids(
                elements,
                reference_element_id=reference_element_id,
                scope=scope,
            )
        )
    if not targets:
        raise ValueError("No target members to delete")
    remaining = [e for e in elements if e.id not in targets]
    return remaining, sorted(targets)


def _next_brace_index(elements: list[ProjectElementMm], assembly_id: str) -> int:
    count = sum(
        1
        for e in elements
        if e.assembly_id == assembly_id and "-brace-custom-" in e.id
    )
    return count + 1


def _next_sketch_member_index(
    elements: list[ProjectElementMm],
    assembly_id: str,
    element_type: str,
) -> int:
    token = element_type.replace("_", "-")
    count = sum(
        1
        for e in elements
        if e.assembly_id == assembly_id and f"-sketch-{token}-" in e.id
    )
    return count + 1


def _round_point(
    point: tuple[float, float, float],
    *,
    step: float = _ENDPOINT_ROUND_MM,
) -> tuple[float, float, float]:
    return tuple(round(c / step) * step for c in point)


def _span_key(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    a = _round_point(start)
    b = _round_point(end)
    return tuple(sorted((a, b)))


def _element_span_key(
    element: ProjectElementMm,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    nodes = element.nodes or {}
    start = nodes.get("start") or nodes.get("bottom")
    end = nodes.get("end") or nodes.get("top")
    if not start or not end or len(start) < 3 or len(end) < 3:
        return None
    return _span_key(
        (float(start[0]), float(start[1]), float(start[2])),
        (float(end[0]), float(end[1]), float(end[2])),
    )


def _remove_members_at_span(
    elements: list[ProjectElementMm],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[list[ProjectElementMm], list[str]]:
    """Drop any member already occupying the same start/end nodes (any type)."""
    key = _span_key(start, end)
    removed: list[str] = []
    out: list[ProjectElementMm] = []
    for element in elements:
        el_key = _element_span_key(element)
        if el_key == key:
            removed.append(element.id)
        else:
            out.append(element)
    return out, removed


def _insert_member_replace_by_span(
    elements: list[ProjectElementMm],
    new_el: ProjectElementMm,
    *,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[list[ProjectElementMm], list[str]]:
    out, removed = _remove_members_at_span(elements, start, end)
    out.append(new_el)
    return out, removed + [new_el.id]


def _member_between_points(
    *,
    element_id: str,
    assembly_id: str,
    profile: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    element_type: str = "bracing",
) -> ProjectElementMm:
    dummy = GridNodeReference(x_axis="A", z_axis="1", elevation="ground")
    member = StructuralMember(
        id=element_id,
        element_type=element_type,  # type: ignore[arg-type]
        profile=profile,
        start_node=dummy,
        end_node=dummy,
    )
    macro = member_from_grid_nodes(
        member,
        assembly_id=assembly_id,
        start=start,
        end=end,
        grid=None,
    )
    if macro is None:
        raise ValueError("Brace length too short")
    return macro_member_to_project_element(macro)


def place_member_between_points(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
    element_type: str = "bracing",
) -> tuple[list[ProjectElementMm], list[str]]:
    ref = elements[0] if elements else None
    aid = assembly_id or (ref.assembly_id if ref else None) or "shed_1"
    defaults = {
        "bracing": "L70x70x7",
        "tie_beam": "IPE200",
        "purlin": "C150x2",
        "beam": "IPE200",
    }
    resolved_type = "tie_beam" if element_type == "beam" else element_type
    prof = profile or defaults.get(element_type, defaults.get(resolved_type, "L70x70x7"))
    if not has_profile(prof):
        prof = "L50x50"
    idx = _next_sketch_member_index(elements, aid, resolved_type)
    token = resolved_type.replace("_", "-")
    eid = f"{aid}-sketch-{token}-{idx}"
    new_el = _member_between_points(
        element_id=eid,
        assembly_id=aid,
        profile=prof,
        start=start_mm,
        end=end_mm,
        element_type=resolved_type,
    )
    return _insert_member_replace_by_span(
        elements,
        new_el,
        start=start_mm,
        end=end_mm,
    )


def place_brace_leg(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    return place_member_between_points(
        elements,
        start_mm=start_mm,
        end_mm=end_mm,
        profile=profile,
        assembly_id=assembly_id,
        element_type="bracing",
    )


def place_bracing_cross(
    elements: list[ProjectElementMm],
    *,
    start_a: tuple[float, float, float],
    end_a: tuple[float, float, float],
    start_b: tuple[float, float, float],
    end_b: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    ref = elements[0] if elements else None
    aid = assembly_id or (ref.assembly_id if ref else None) or "shed_1"
    prof = profile or "L70x70x7"
    if not has_profile(prof):
        prof = "L50x50"
    idx = _next_brace_index(elements, aid)
    leg_a = _member_between_points(
        element_id=f"{aid}-brace-custom-{idx}-a",
        assembly_id=aid,
        profile=prof,
        start=start_a,
        end=end_a,
    )
    if _span_key(start_a, end_a) == _span_key(start_b, end_b):
        raise ValueError(
            "X-brace complement matches the sketched leg — pick corners on opposite diagonals."
        )
    leg_b = _member_between_points(
        element_id=f"{aid}-brace-custom-{idx}-b",
        assembly_id=aid,
        profile=prof,
        start=start_b,
        end=end_b,
    )
    out = list(elements)
    removed: list[str] = []
    out, removed_a = _remove_members_at_span(out, start_a, end_a)
    removed.extend(removed_a)
    out, removed_b = _remove_members_at_span(out, start_b, end_b)
    removed.extend(removed_b)
    out.append(leg_a)
    out.append(leg_b)
    changed = list(dict.fromkeys(removed + [leg_a.id, leg_b.id]))
    return out, changed


def place_x_brace_from_leg(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    start_element_id: str | None = None,
    end_element_id: str | None = None,
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    from core.brace_geometry import infer_x_brace_corners

    corners = infer_x_brace_corners(
        start_mm,
        end_mm,
        elements,
        start_element_id=start_element_id,
        end_element_id=end_element_id,
    )
    if corners is None:
        raise ValueError(
            "Could not infer X-brace corners from the sketched leg — try picking grid joints."
        )
    a, b, c, d = corners
    return place_bracing_cross(
        elements,
        start_a=a,
        end_a=b,
        start_b=c,
        end_b=d,
        profile=profile,
        assembly_id=assembly_id,
    )


def _grid_engine_from_context(ctx: GridPlacementContext) -> StructuralGridEngine:
    style = ctx.roof_style if ctx.roof_style in ("duo_pitch", "mono_pitch", "flat") else "duo_pitch"
    pitch = 0.0 if style == "flat" else float(ctx.roof_pitch_deg)
    gd = GridDefinition(
        x_spans=list(ctx.x_spans),
        z_spans=list(ctx.z_spans),
        height_mm=float(ctx.height_mm),
        roof_pitch_deg=pitch,
        roof_style=style,  # type: ignore[arg-type]
        mono_high_side=ctx.mono_high_side if ctx.mono_high_side in ("A", "B") else "B",  # type: ignore[arg-type]
    )
    return StructuralGridEngine.from_definition(gd)


def _infer_assembly_id(elements: list[ProjectElementMm], fallback: str) -> str:
    for element in elements:
        if element.assembly_id:
            return str(element.assembly_id)
    return fallback


def _member_to_element(
    member: StructuralMember,
    *,
    assembly_id: str,
    grid: StructuralGridEngine,
) -> ProjectElementMm:
    start = grid.resolve_node(member.start_node)
    end = grid.resolve_node(member.end_node)
    macro = member_from_grid_nodes(
        member,
        assembly_id=assembly_id,
        start=start,
        end=end,
        grid=grid,
    )
    if macro is None:
        raise ValueError(f"Member {member.id} is too short to place")
    return macro_member_to_project_element(macro)


def place_grid_column(
    elements: list[ProjectElementMm],
    *,
    x_axis: str,
    z_axis: str,
    profile: str,
    grid: GridPlacementContext,
    trussed_z_labels: Iterable[str] | None = None,
    assembly_id: str | None = None,
    offset_mm: dict[str, float] | None = None,
    connect_to: str = "auto",
    truss_type: str = "pratt",
    add_tie_in_bay: bool = False,
    tie_profile: str | None = None,
    bay_z_start: str | None = None,
    bay_z_end: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    engine = _grid_engine_from_context(grid)
    x = x_axis.strip().upper()
    z = z_axis.strip()
    off = dict(offset_mm or {})
    try:
        engine.resolve_x_mm(x)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    try:
        engine.resolve_z_mm(z)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    trussed = list(trussed_z_labels or [])
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    off_token = ""
    if off:
        off_token = "-o" + _grid_axis_token(
            "_".join(f"{k}{v}" for k, v in sorted(off.items()))
        )
    eid = f"{aid}-col-{x}-{_grid_axis_token(z)}{off_token}"

    member = structural_member_for_column(
        element_id=eid,
        profile=profile,
        x_axis=x,
        z_axis=z,
        offset_mm=off,
        engine=engine,
        trussed_z_labels=trussed,
        truss_type=truss_type,
        connect_to=connect_to,
    )
    new_el = _member_to_element(member, assembly_id=aid, grid=engine)

    out: list[ProjectElementMm] = []
    changed: list[str] = []
    replaced = False
    for element in elements:
        if element.id == eid:
            out.append(new_el)
            replaced = True
            changed.append(eid)
        else:
            out.append(element)
    if not replaced:
        out.append(new_el)
        changed.append(eid)

    if add_tie_in_bay and bay_z_start and bay_z_end:
        tie_prof = tie_profile or "IPE200"
        if has_profile(tie_prof):
            out, tie_ids = place_grid_tie_beam(
                out,
                x_axis=x,
                z_start=bay_z_start,
                z_end=bay_z_end,
                profile=tie_prof,
                grid=grid,
                assembly_id=aid,
            )
            changed.extend(tie_ids)

    return out, changed


def _trussed_frame_z_labels(elements: list[ProjectElementMm]) -> set[str]:
    trussed: set[str] = set()
    for element in elements:
        match = _TRUSS_RE.match(element.id)
        if match:
            trussed.add(match.group("z"))
    return trussed


def _place_roof_x_for_bay(
    elements: list[ProjectElementMm],
    *,
    engine: StructuralGridEngine,
    bay_index: int,
    profile: str | None,
    assembly_id: str,
) -> tuple[list[ProjectElementMm], list[str]]:
    from core.grid_member_catalog import _ridge_label, _roof_bracing

    z_labels = engine.z_labels
    z0 = z_labels[bay_index]
    z1 = z_labels[bay_index + 1]
    trussed = _trussed_frame_z_labels(elements)
    use_truss = z0 in trussed or z1 in trussed
    ridge = _ridge_label(engine)
    members = _roof_bracing(
        engine,
        assembly_id,
        bay_index,
        z0,
        z1,
        ridge,
        profile or "L70x70x7",
        truss_type="pratt",
        use_truss=use_truss,
    )
    out = list(elements)
    changed: list[str] = []
    for i in range(0, len(members), 2):
        if i + 1 >= len(members):
            break
        leg_a, leg_b = members[i], members[i + 1]
        start_a = engine.resolve_node(leg_a.start_node)
        end_a = engine.resolve_node(leg_a.end_node)
        start_b = engine.resolve_node(leg_b.start_node)
        end_b = engine.resolve_node(leg_b.end_node)
        out, cross_changed = place_bracing_cross(
            out,
            start_a=start_a,
            end_a=end_a,
            start_b=start_b,
            end_b=end_b,
            profile=profile,
            assembly_id=assembly_id,
        )
        changed.extend(cross_changed)
    return out, changed


def _place_gable_x_brace(
    elements: list[ProjectElementMm],
    *,
    x_bay_index: int,
    frame_z: str,
    x_start: str | None = None,
    x_end: str | None = None,
    profile: str | None = None,
    assembly_id: str | None = None,
    grid: GridPlacementContext,
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel",
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place vertical X-bracing on gable end-wall panel(s) at a fixed Z frame."""
    engine = _grid_engine_from_context(grid)
    x_labels = engine.x_labels
    z_labels = engine.z_labels
    if len(x_labels) < 2:
        raise ValueError("Grid must have at least two X lines for gable bracing")

    z_label = frame_z.strip()
    try:
        engine.resolve_z_mm(z_label)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if z_label not in z_labels:
        raise ValueError(f"Unknown frame {z_label}")

    if x_start and x_end:
        xa = x_start.strip().upper()
        xb = x_end.strip().upper()
    elif 0 <= x_bay_index < len(x_labels) - 1:
        xa = x_labels[x_bay_index]
        xb = x_labels[x_bay_index + 1]
    else:
        raise ValueError(f"Invalid X bay index {x_bay_index}")

    for label in (xa, xb):
        try:
            engine.resolve_x_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    def corners_for_gable(x_left: str, x_right: str, z: str) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        a = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z, elevation="ground")
        )
        b = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z, elevation="eave")
        )
        c = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z, elevation="eave")
        )
        d = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z, elevation="ground")
        )
        return a, b, c, d

    def panels_to_place() -> list[tuple[str, str, str]]:
        near_z, far_z = z_labels[0], z_labels[-1]
        if scope == "this_panel" or scope == "portal_bay":
            return [(xa, xb, z_label)]
        if scope == "parallel_bay":
            other = far_z if z_label == near_z else near_z
            if other == z_label:
                return [(xa, xb, z_label)]
            return list(dict.fromkeys([(xa, xb, z_label), (xa, xb, other)]))
        if scope == "all_bays_wall":
            return [
                (x_labels[bi], x_labels[bi + 1], z_label)
                for bi in range(len(x_labels) - 1)
            ]
        return [
            (x_labels[bi], x_labels[bi + 1], zl)
            for zl in (near_z, far_z)
            for bi in range(len(x_labels) - 1)
        ]

    out = list(elements)
    changed: list[str] = []
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    for x_left, x_right, zl in panels_to_place():
        a, b, c, d = corners_for_gable(x_left, x_right, zl)
        out, panel_changed = place_bracing_cross(
            out,
            start_a=a,
            end_a=b,
            start_b=c,
            end_b=d,
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(panel_changed)
    if not changed:
        raise ValueError(
            f"Could not place gable bracing at frame {z_label} — "
            "check the selected panel and grid references."
        )
    return out, list(dict.fromkeys(changed))


def place_wall_x_brace(
    elements: list[ProjectElementMm],
    *,
    wall_x: str,
    bay_index: int,
    profile: str | None = None,
    assembly_id: str | None = None,
    grid: GridPlacementContext,
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel",
    panel_kind: Literal["long_wall", "gable_wall"] = "long_wall",
    frame_z: str | None = None,
    z_start: str | None = None,
    z_end: str | None = None,
    x_start: str | None = None,
    x_end: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place vertical X-bracing on long-side or gable end-wall panel(s)."""
    if panel_kind == "gable_wall":
        if not frame_z:
            raise ValueError("frame_z is required for gable wall bracing")
        return _place_gable_x_brace(
            elements,
            x_bay_index=bay_index,
            frame_z=frame_z,
            x_start=x_start,
            x_end=x_end,
            profile=profile,
            assembly_id=assembly_id,
            grid=grid,
            scope=scope,
        )

    from core.grid_member_catalog import _column_top_elev

    engine = _grid_engine_from_context(grid)
    z_labels = engine.z_labels
    x_labels = engine.x_labels
    if len(x_labels) < 2:
        raise ValueError("Grid must have at least two X lines for wall bracing")

    wall = wall_x.strip().upper()
    try:
        engine.resolve_x_mm(wall)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if z_start and z_end:
        z0_label = z_start.strip()
        z1_label = z_end.strip()
    elif 0 <= bay_index < len(z_labels) - 1:
        z0_label = z_labels[bay_index]
        z1_label = z_labels[bay_index + 1]
    else:
        raise ValueError(f"Invalid bay_index {bay_index}")

    for label in (z0_label, z1_label):
        try:
            engine.resolve_z_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    def corners_for_bay(
        wall_label: str,
        z0_label: str,
        z1_label: str,
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        top = _column_top_elev(engine, wall_label)
        a = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z0_label, elevation="ground")
        )
        b = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z1_label, elevation=top)
        )
        c = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z0_label, elevation=top)
        )
        d = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z1_label, elevation="ground")
        )
        return a, b, c, d

    def panels_to_place() -> list[tuple[str, str, str]]:
        if scope == "this_panel":
            return [(wall, z0_label, z1_label)]
        if scope == "parallel_bay":
            opposite = (
                x_labels[-1] if wall == x_labels[0] else x_labels[0]
            )
            if opposite == wall:
                return [(wall, z0_label, z1_label)]
            return list(
                dict.fromkeys(
                    [
                        (wall, z0_label, z1_label),
                        (opposite, z0_label, z1_label),
                    ]
                )
            )
        if scope == "portal_bay":
            return [
                (x_labels[0], z0_label, z1_label),
                (x_labels[-1], z0_label, z1_label),
            ]
        if scope == "all_bays_wall":
            return [
                (wall, z_labels[bi], z_labels[bi + 1])
                for bi in range(len(z_labels) - 1)
            ]
        side_walls = [x_labels[0], x_labels[-1]]
        return [
            (wall_label, z_labels[bi], z_labels[bi + 1])
            for wall_label in side_walls
            for bi in range(len(z_labels) - 1)
        ]

    out = list(elements)
    changed: list[str] = []
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    for wall_label, zs, ze in panels_to_place():
        a, b, c, d = corners_for_bay(wall_label, zs, ze)
        out, panel_changed = place_bracing_cross(
            out,
            start_a=a,
            end_a=b,
            start_b=c,
            end_b=d,
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(panel_changed)
    if scope == "portal_bay":
        out, roof_changed = _place_roof_x_for_bay(
            out,
            engine=engine,
            bay_index=bay_index,
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(roof_changed)
    return out, list(dict.fromkeys(changed))


def place_grid_tie_beam(
    elements: list[ProjectElementMm],
    *,
    x_axis: str,
    z_start: str,
    z_end: str,
    profile: str,
    elevation: str = "eave",
    grid: GridPlacementContext,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    engine = _grid_engine_from_context(grid)
    x = x_axis.strip().upper()
    zs = z_start.strip()
    ze = z_end.strip()
    try:
        engine.resolve_x_mm(x)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    for label in (zs, ze):
        try:
            engine.resolve_z_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    elev = elevation.strip().lower()
    eid = f"{aid}-tie-bay-{x}-{_grid_axis_token(zs)}-{_grid_axis_token(ze)}-{elev}"

    start_ref = GridNodeReference(x_axis=x, z_axis=zs, elevation=elev)
    end_ref = GridNodeReference(x_axis=x, z_axis=ze, elevation=elev)
    member = StructuralMember(
        id=eid,
        element_type="tie_beam",
        profile=profile,
        start_node=start_ref,
        end_node=end_ref,
    )
    new_el = _member_to_element(member, assembly_id=aid, grid=engine)
    nodes = new_el.nodes or {}
    start = nodes.get("start")
    end = nodes.get("end")
    if not start or not end:
        raise ValueError("Tie beam nodes missing after placement")
    start_mm = (float(start[0]), float(start[1]), float(start[2]))
    end_mm = (float(end[0]), float(end[1]), float(end[2]))
    return _insert_member_replace_by_span(
        elements,
        new_el,
        start=start_mm,
        end=end_mm,
    )


def collect_snap_nodes(
    elements: list[ProjectElementMm],
    *,
    tolerance_mm: float = 250.0,
) -> list[tuple[str, tuple[float, float, float]]]:
    """Merge connection nodes from all members for viewport snapping."""
    buckets: dict[tuple[int, int, int], tuple[str, tuple[float, float, float]]] = {}
    scale = max(tolerance_mm, 50.0)

    def bucket_key(x: float, y: float, z: float) -> tuple[int, int, int]:
        return (
            round(x / scale),
            round(y / scale),
            round(z / scale),
        )

    for element in elements:
        nodes = element.nodes or {}
        for name, coords in nodes.items():
            if not isinstance(coords, (list, tuple)) or len(coords) < 3:
                continue
            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
            key = bucket_key(x, y, z)
            nid = f"{element.id}:{name}"
            if key not in buckets:
                buckets[key] = (nid, (x, y, z))

    return list(buckets.values())
