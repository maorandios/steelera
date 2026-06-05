"""
Deterministically expand universal structural operations into uniform members.

This is the element-agnostic kernel: it knows how to repeat/connect members across
a grid, but nothing about "sheds". Adding new element types requires NO changes here.
"""

from __future__ import annotations

from core.spatial_grid import StructuralGridEngine
from schemas.spatial_grid import GridNodeReference, StructuralGridLayout, StructuralMember
from schemas.structural_ops import (
    ALL,
    ArrayAdjacentOp,
    ArrayMemberOp,
    DefineLevelOp,
    Operation,
    PlaceMemberOp,
    StructuralDesign,
)


def _resolve_lines(selector: list[str], all_labels: list[str]) -> list[str]:
    if selector == [ALL]:
        return list(all_labels)
    return list(selector)


def _node(x: str, z: str, elev: str) -> GridNodeReference:
    return GridNodeReference(x_axis=x, z_axis=z, elevation=elev)


def _expand_array_member(
    op: ArrayMemberOp, engine: StructuralGridEngine
) -> list[StructuralMember]:
    xs = _resolve_lines(op.x_lines, engine.x_labels) if op.x_lines else [None]
    zs = _resolve_lines(op.z_lines, engine.z_labels) if op.z_lines else [None]
    members: list[StructuralMember] = []
    idx = 0
    for x in xs:
        for z in zs:
            start = op.start_node.model_copy()
            end = op.end_node.model_copy()
            if x is not None:
                start = start.model_copy(update={"x_axis": x})
                end = end.model_copy(update={"x_axis": x})
            if z is not None:
                start = start.model_copy(update={"z_axis": z})
                end = end.model_copy(update={"z_axis": z})
            tag_x = x if x is not None else start.x_axis
            tag_z = z if z is not None else start.z_axis
            members.append(
                StructuralMember(
                    id=f"{op.id_prefix}-{tag_x}-{tag_z}-{idx}",
                    element_type=op.element_type,
                    profile=op.profile,
                    start_node=start,
                    end_node=end,
                )
            )
            idx += 1
    return members


def _expand_array_adjacent(
    op: ArrayAdjacentOp, engine: StructuralGridEngine
) -> list[StructuralMember]:
    if op.axis == "z":
        lines = engine.z_labels
        at = _resolve_lines(op.at_lines, engine.x_labels)
    else:
        lines = engine.x_labels
        at = _resolve_lines(op.at_lines, engine.z_labels)

    members: list[StructuralMember] = []
    idx = 0
    for i in range(len(lines) - 1):
        a_line, b_line = lines[i], lines[i + 1]
        for other in at:
            if op.axis == "z":
                start = _node(other, a_line, op.elevation_start)
                end = _node(other, b_line, op.elevation_end)
            else:
                start = _node(a_line, other, op.elevation_start)
                end = _node(b_line, other, op.elevation_end)
            members.append(
                StructuralMember(
                    id=f"{op.id_prefix}-{op.axis}{i}-{other}-{idx}",
                    element_type=op.element_type,
                    profile=op.profile,
                    start_node=start,
                    end_node=end,
                )
            )
            idx += 1
    return members


def expand_design(design: StructuralDesign) -> StructuralGridLayout:
    """Expand operations → resolvable StructuralGridLayout (custom levels merged in)."""
    custom_levels: dict[str, float] = dict(design.grid_definition.custom_levels or {})
    for op in design.operations:
        if isinstance(op, DefineLevelOp):
            name = op.name.strip()
            lower = name.lower()
            norm = lower.replace(" ", "_").replace("-", "_")
            for key in (name, lower, norm):
                custom_levels[key] = float(op.height_mm)

    grid_def = design.grid_definition.model_copy(
        update={"custom_levels": custom_levels}
    )
    engine = StructuralGridEngine.from_definition(grid_def)

    members: list[StructuralMember] = []
    seen_ids: set[str] = set()
    for op in design.operations:
        if isinstance(op, DefineLevelOp):
            continue
        if isinstance(op, PlaceMemberOp):
            produced = [
                StructuralMember(
                    id=op.id,
                    element_type=op.element_type,
                    profile=op.profile,
                    start_node=op.start_node,
                    end_node=op.end_node,
                )
            ]
        elif isinstance(op, ArrayMemberOp):
            produced = _expand_array_member(op, engine)
        elif isinstance(op, ArrayAdjacentOp):
            produced = _expand_array_adjacent(op, engine)
        else:  # pragma: no cover - discriminated union is exhaustive
            raise ValueError(f"Unknown operation: {op!r}")

        for m in produced:
            mid = m.id
            bump = 1
            while mid in seen_ids:
                mid = f"{m.id}_{bump}"
                bump += 1
            seen_ids.add(mid)
            members.append(m.model_copy(update={"id": mid}) if mid != m.id else m)

    return StructuralGridLayout(
        assembly_id=design.assembly_id,
        replace_existing=design.replace_existing,
        grid_definition=grid_def,
        structural_members=members,
    )
