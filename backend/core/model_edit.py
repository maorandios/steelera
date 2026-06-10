"""Deterministic surgical edits on an existing project model."""

from __future__ import annotations

import math
import re
from typing import Iterable

from catalog_loader import get_profile, has_profile
from core.geometry_engine import macro_member_to_project_element
from core.grid_member_catalog import _column_top_for_frame
from core.member_resolver import member_from_grid_nodes
from core.spatial_grid import StructuralGridEngine
from schemas.elements import ProjectElementMm, SectionDimensionsMm
from schemas.model_edit import GridPlacementContext
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralMember

_AXIS_SAFE_RE = re.compile(r"[^A-Za-z0-9]+")

_BRACE_PAIR_RE = re.compile(r"^(?P<prefix>.+)-([ab])$", re.IGNORECASE)


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


def place_brace_leg(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    ref = elements[0] if elements else None
    aid = assembly_id or (ref.assembly_id if ref else None) or "shed_1"
    prof = profile or "L70x70x7"
    if not has_profile(prof):
        prof = "L50x50"
    idx = _next_brace_index(elements, aid)
    eid = f"{aid}-brace-custom-{idx}-a"
    new_el = _member_between_points(
        element_id=eid,
        assembly_id=aid,
        profile=prof,
        start=start_mm,
        end=end_mm,
    )
    return [*elements, new_el], [eid]


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
    leg_b = _member_between_points(
        element_id=f"{aid}-brace-custom-{idx}-b",
        assembly_id=aid,
        profile=prof,
        start=start_b,
        end=end_b,
    )
    return [*elements, leg_a, leg_b], [leg_a.id, leg_b.id]


def _grid_axis_token(value: str) -> str:
    """Encode grid axis for element ids (2+1/2 → 2p1p2)."""
    return _AXIS_SAFE_RE.sub("p", value.strip())


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
) -> tuple[list[ProjectElementMm], list[str]]:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    engine = _grid_engine_from_context(grid)
    x = x_axis.strip().upper()
    z = z_axis.strip()
    try:
        engine.resolve_x_mm(x)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    try:
        engine.resolve_z_mm(z)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    trussed = set(trussed_z_labels or [])
    top = _column_top_for_frame(engine, x, z, trussed)
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    eid = f"{aid}-col-{x}-{_grid_axis_token(z)}"

    start_ref = GridNodeReference(x_axis=x, z_axis=z, elevation="ground")
    end_ref = GridNodeReference(x_axis=x, z_axis=z, elevation=top)
    member = StructuralMember(
        id=eid,
        element_type="column",
        profile=profile,
        start_node=start_ref,
        end_node=end_ref,
    )
    new_el = _member_to_element(member, assembly_id=aid, grid=engine)

    replaced = False
    out: list[ProjectElementMm] = []
    for element in elements:
        if element.id == eid:
            out.append(new_el)
            replaced = True
        else:
            out.append(element)
    if not replaced:
        out.append(new_el)
    return out, [eid]


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

    replaced = False
    out: list[ProjectElementMm] = []
    for element in elements:
        if element.id == eid:
            out.append(new_el)
            replaced = True
        else:
            out.append(element)
    if not replaced:
        out.append(new_el)
    return out, [eid]


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
