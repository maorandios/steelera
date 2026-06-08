"""
Build IFC topology (nodes, entities, assemblies) from resolved macro members.

Does not alter geometry — consumes output of member_resolver only.
"""

from __future__ import annotations

import math
import re
from typing import Any

from schemas.ifc_model import IFCEntity, IFCNode, IFCTopology, StructuralAssembly
from schemas.spatial_grid import GridNodeReference, StructuralGridLayout, StructuralMember

_NODE_TOL_MM = 0.1

_COL_RE = re.compile(r"-col-[A-Z]+-(\d+)$")
_RAFTER_RE = re.compile(r"-rafter-(?:L|R)-(\d+)$")
_TRUSS_RE = re.compile(r"-truss-(?:tc|bc|web|post)-(\d+)")
_HAUNCH_RE = re.compile(r"-haunch-(\d+)-")
_FLY_RE = re.compile(r"-fly-(\d+)-")
_GABLE_GIRT_RE = re.compile(r"-gablegirt-(\d+)-")
_GABLE_POST_RE = re.compile(r"-gablepost-(\d+)-")
_BASEPLATE_RE = re.compile(r"-baseplate-([A-Z]+-\d+|gp-\d+-\d+)$")


class NodeRegistry:
    """Deduplicate absolute mm coordinates into stable node ids."""

    def __init__(self, tolerance_mm: float = _NODE_TOL_MM) -> None:
        self._tolerance = tolerance_mm
        self._coord_to_id: dict[tuple[float, float, float], str] = {}
        self._nodes: dict[str, IFCNode] = {}

    def _key(self, xyz: list[float] | tuple[float, ...]) -> tuple[float, float, float]:
        t = self._tolerance
        return (
            round(float(xyz[0]) / t) * t,
            round(float(xyz[1]) / t) * t,
            round(float(xyz[2]) / t) * t,
        )

    def get_or_create(
        self,
        xyz: list[float],
        *,
        hint: str | None = None,
    ) -> str:
        key = self._key(xyz)
        existing = self._coord_to_id.get(key)
        if existing is not None:
            return existing
        node_id = hint or f"N_{len(self._nodes):04d}"
        while node_id in self._nodes:
            node_id = f"{node_id}_{len(self._nodes)}"
        self._coord_to_id[key] = node_id
        self._nodes[node_id] = IFCNode(id=node_id, x=key[0], y=key[1], z=key[2])
        return node_id

    def as_dict(self) -> dict[str, IFCNode]:
        return dict(self._nodes)


def _node_hint(ref: GridNodeReference) -> str:
    elev = (
        str(ref.elevation)
        .strip()
        .upper()
        .replace("+", "_")
        .replace("/", "_")
        .replace("-", "_")
    )
    x = str(ref.x_axis).strip().upper().replace("+", "_").replace("/", "_")
    z = str(ref.z_axis).strip().upper().replace("+", "_").replace("/", "_")
    return f"N_Z{z}_X{x}_{elev}"


def _ifc_type(element_type: str) -> str:
    if element_type == "column":
        return "IfcColumn"
    if element_type == "base_plate":
        return "IfcPlate"
    if element_type in (
        "rafter",
        "truss_chord",
        "tie_beam",
        "purlin",
        "wall_girt",
    ):
        return "IfcBeam"
    return "IfcMember"


def _structural_role(element_type: str, member_id: str) -> str:
    if element_type == "column":
        return "COLUMN"
    if element_type == "rafter":
        return "RAFTER"
    if element_type == "purlin":
        return "PURLIN"
    if element_type == "wall_girt":
        return "GIRT"
    if element_type == "tie_beam":
        return "TIE_BEAM"
    if element_type == "base_plate":
        return "BASE_PLATE"
    if element_type == "sag_rod":
        return "SAG_ROD"
    if element_type == "haunch":
        return "HAUNCH"
    if element_type == "fly_brace":
        return "FLY_BRACE"
    if element_type in ("bracing", "x_brace"):
        return "BRACING"
    if element_type == "truss_web":
        if "-truss-post-" in member_id:
            return "VERTICAL"
        return "DIAGONAL"
    if element_type == "truss_chord":
        if "-truss-tc-" in member_id:
            return "TOP_CHORD"
        if "-truss-bc-" in member_id:
            return "BOTTOM_CHORD"
        if "-truss-post-" in member_id:
            return "VERTICAL"
        return "CHORD"
    return element_type.upper()


def _is_truss_member(entity_id: str, element_type: str) -> bool:
    return "-truss-" in entity_id or element_type in ("truss_chord", "truss_web")


def _truss_z_label(member_id: str) -> str | None:
    m = _TRUSS_RE.search(member_id)
    return m.group(1) if m else None


def _portal_z_label(member_id: str, element_type: str) -> str | None:
    if _is_truss_member(member_id, element_type):
        return None
    for pattern in (_COL_RE, _RAFTER_RE, _HAUNCH_RE, _FLY_RE):
        m = pattern.search(member_id)
        if m:
            return m.group(1)
    m = _BASEPLATE_RE.search(member_id)
    if m:
        tag = m.group(1)
        if tag.startswith("gp-"):
            parts = tag.split("-")
            return parts[1] if len(parts) > 1 else None
        parts = tag.rsplit("-", 1)
        return parts[-1] if len(parts) == 2 else None
    return None


def _gable_z_label(member_id: str) -> str | None:
    for pattern in (_GABLE_GIRT_RE, _GABLE_POST_RE):
        m = pattern.search(member_id)
        if m:
            return m.group(1)
    return None


def _assembly_id_building(building_id: str) -> str:
    return f"ASM_{building_id.upper()}"


def _assembly_id_portal(z_label: str) -> str:
    return f"ASM_PORTAL_Z{z_label}"


def _assembly_id_truss(z_label: str) -> str:
    return f"ASM_TRUSS_Z{z_label}"


def _assembly_id_singleton(entity_id: str) -> str:
    return f"ASM_SINGLE_{entity_id}"


def _classify_assemblies(
    entity_id: str,
    element_type: str,
    *,
    building_id: str,
) -> tuple[str, list[str]]:
    """Return (primary_assembly_id, all assembly_ids).

  Physical sub-assemblies (truss, portal line, roof, walls) are mutually exclusive
  for highlight — truss members never share a portal assembly bucket with columns.
    """
    building = _assembly_id_building(building_id)

    if _is_truss_member(entity_id, element_type):
        z = _truss_z_label(entity_id)
        if z:
            truss = _assembly_id_truss(z)
            return truss, [building, truss]
        single = _assembly_id_singleton(entity_id)
        return single, [building, single]

    if element_type == "purlin" or "-sag-roof-" in entity_id:
        roof = "ASM_ROOF"
        return roof, [building, roof]

    gable_z = _gable_z_label(entity_id)
    if gable_z is not None:
        gable = f"ASM_GABLE_Z{gable_z}"
        return gable, [building, gable]

    if "-girt-A-" in entity_id or "-sag-wall-A-" in entity_id:
        wall = "ASM_WALL_A"
        return wall, [building, wall]

    if "-girt-B-" in entity_id or "-sag-wall-B-" in entity_id:
        wall = "ASM_WALL_B"
        return wall, [building, wall]

    if "-sag-gable-" in entity_id:
        m = re.search(r"-sag-gable-(\d+)-", entity_id)
        if m:
            gable = f"ASM_GABLE_Z{m.group(1)}"
            return gable, [building, gable]

    if element_type == "tie_beam" or "-tie-" in entity_id or "-bctie-" in entity_id:
        longi = "ASM_LONGITUDINAL"
        return longi, [building, longi]

    portal_z = _portal_z_label(entity_id, element_type)
    if portal_z is not None:
        portal = _assembly_id_portal(portal_z)
        return portal, [building, portal]

    if (
        element_type in ("bracing", "x_brace", "sag_rod")
        or "-brace-" in entity_id
    ):
        br = "ASM_BRACING"
        return br, [building, br]

    single = _assembly_id_singleton(entity_id)
    return single, [building, single]


def _rotation_euler_deg(macro: dict[str, Any]) -> list[float]:
    rotation = macro.get("rotation") or [0.0, 0.0, 0.0]
    if not rotation:
        return [0.0, 0.0, 0.0]
    out = [float(rotation[i]) if i < len(rotation) else 0.0 for i in range(3)]
    return out


def _is_vertical_member(start: list[float], end: list[float]) -> bool:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.hypot(dx, math.hypot(dy, dz))
    if length < 1e-6:
        return False
    return abs(dy) >= abs(dx) and abs(dy) >= abs(dz)


def build_ifc_topology(
    macro_members: list[dict[str, Any]],
    *,
    building_id: str = "shed_1",
    members_by_id: dict[str, StructuralMember] | None = None,
) -> IFCTopology:
    registry = NodeRegistry()
    members_by_id = members_by_id or {}
    entities: list[IFCEntity] = []
    entity_assemblies: dict[str, list[str]] = {}

    for macro in macro_members:
        member_id = str(macro["id"])
        element_type = str(macro.get("element_type") or "")
        nodes = macro.get("nodes") or {}
        start = nodes.get("start")
        end = nodes.get("end")
        if not start or not end:
            continue

        source = members_by_id.get(member_id)
        start_hint = (
            _node_hint(source.start_node) if source is not None else None
        )
        end_hint = _node_hint(source.end_node) if source is not None else None

        start_id = registry.get_or_create(list(start), hint=start_hint)
        end_id = registry.get_or_create(list(end), hint=end_hint)

        role = _structural_role(element_type, member_id)
        if element_type == "truss_web" and _is_vertical_member(start, end):
            role = "VERTICAL"

        primary, assembly_ids = _classify_assemblies(
            member_id, element_type, building_id=building_id
        )

        entity = IFCEntity(
            id=member_id,
            start_node_id=start_id,
            end_node_id=end_id,
            ifc_type=_ifc_type(element_type),  # type: ignore[arg-type]
            structural_role=role,
            profile_family=str(macro.get("profile") or ""),
            local_rotation=_rotation_euler_deg(macro)[0],
            rotation_euler=_rotation_euler_deg(macro),
            alignment=str(macro.get("alignment") or "center"),
            primary_assembly_id=primary,
            assembly_ids=assembly_ids,
        )
        entities.append(entity)
        entity_assemblies[member_id] = assembly_ids

    assemblies = _build_assembly_tree(
        building_id=building_id,
        entities=entities,
    )

    return IFCTopology(
        building_id=building_id,
        nodes=registry.as_dict(),
        entities=entities,
        assemblies=assemblies,
        entity_assemblies=entity_assemblies,
    )


def _build_assembly_tree(
    *,
    building_id: str,
    entities: list[IFCEntity],
) -> dict[str, StructuralAssembly]:
    building_asm_id = _assembly_id_building(building_id)
    buckets: dict[str, list[str]] = {building_asm_id: []}

    for entity in entities:
        buckets[building_asm_id].append(entity.id)
        for asm_id in entity.assembly_ids:
            if asm_id == building_asm_id:
                continue
            buckets.setdefault(asm_id, []).append(entity.id)

    assemblies: dict[str, StructuralAssembly] = {
        building_asm_id: StructuralAssembly(
            id=building_asm_id,
            label=f"Building ({building_id})",
            assembly_type="BUILDING",
            parent_id=None,
            entity_ids=sorted(set(buckets.get(building_asm_id, []))),
        )
    }

    for asm_id, entity_ids in buckets.items():
        if asm_id == building_asm_id:
            continue
        unique = sorted(set(entity_ids))
        if not unique:
            continue
        asm_type, label, parent = _assembly_meta(asm_id, building_asm_id)
        assemblies[asm_id] = StructuralAssembly(
            id=asm_id,
            label=label,
            assembly_type=asm_type,  # type: ignore[arg-type]
            parent_id=parent,
            entity_ids=unique,
        )

    return assemblies


def _assembly_meta(
    asm_id: str,
    building_asm_id: str,
) -> tuple[str, str, str | None]:
    if asm_id.startswith("ASM_PORTAL_Z"):
        z = asm_id.removeprefix("ASM_PORTAL_Z")
        return "PORTAL", f"Portal line {z}", building_asm_id
    if asm_id.startswith("ASM_TRUSS_Z"):
        z = asm_id.removeprefix("ASM_TRUSS_Z")
        return "TRUSS", f"Truss {z}", building_asm_id
    if asm_id == "ASM_ROOF":
        return "ROOF", "Roof (purlins)", building_asm_id
    if asm_id == "ASM_WALL_A":
        return "WALL_SIDE", "Wall A", building_asm_id
    if asm_id == "ASM_WALL_B":
        return "WALL_SIDE", "Wall B", building_asm_id
    if asm_id.startswith("ASM_GABLE_Z"):
        z = asm_id.removeprefix("ASM_GABLE_Z")
        return "WALL_GABLE", f"Gable wall {z}", building_asm_id
    if asm_id == "ASM_LONGITUDINAL":
        return "LONGITUDINAL", "Longitudinal ties", building_asm_id
    if asm_id == "ASM_BRACING":
        return "BRACING", "Bracing", building_asm_id
    if asm_id.startswith("ASM_SINGLE_"):
        return "MEMBER", asm_id.removeprefix("ASM_SINGLE_"), building_asm_id
    return "BUILDING", asm_id, building_asm_id


def build_topology_from_layout(layout: StructuralGridLayout) -> IFCTopology:
    from core.grid_layout_utils import ensure_layout_members
    from core.member_resolver import layout_to_macro_members

    layout = ensure_layout_members(layout)
    members_by_id = {m.id: m for m in layout.structural_members}
    macro_members = layout_to_macro_members(layout)
    return build_ifc_topology(
        macro_members,
        building_id=layout.assembly_id,
        members_by_id=members_by_id,
    )


def stamp_elements_with_topology(
    elements: list[Any],
    topology: IFCTopology,
) -> list[Any]:
    """Attach assembly ids to project elements for client-side highlight."""
    entity_map = {e.id: e for e in topology.entities}
    stamped = []
    for element in elements:
        entity = entity_map.get(element.id)
        if entity is None:
            stamped.append(element)
            continue
        stamped.append(
            element.model_copy(
                update={
                    "primary_assembly_id": entity.primary_assembly_id,
                    "assembly_ids": entity.assembly_ids,
                }
            )
        )
    return stamped
