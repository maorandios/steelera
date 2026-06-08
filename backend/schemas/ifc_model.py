"""IFC-oriented structural topology: nodes, entities, and assembly hierarchy."""

from typing import Literal

from pydantic import BaseModel, Field

IFCTypeLiteral = Literal["IfcColumn", "IfcBeam", "IfcMember", "IfcPlate"]

AssemblyTypeLiteral = Literal[
    "BUILDING",
    "PORTAL",
    "TRUSS",
    "ROOF",
    "WALL_SIDE",
    "WALL_GABLE",
    "LONGITUDINAL",
    "BRACING",
    "MEMBER",
]


class IFCNode(BaseModel):
    """Unique connection point in mm (backend coords: Y vertical)."""

    id: str
    x: float
    y: float
    z: float


class IFCEntity(BaseModel):
    """Structural member for IFC export and assembly grouping."""

    id: str
    start_node_id: str
    end_node_id: str
    ifc_type: IFCTypeLiteral
    structural_role: str
    profile_family: str
    local_rotation: float = 0.0
    rotation_euler: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    alignment: str = "center"
    primary_assembly_id: str
    assembly_ids: list[str] = Field(default_factory=list)


class StructuralAssembly(BaseModel):
    """Grouped members (portal frame, truss, roof plane, wall, etc.)."""

    id: str
    label: str
    assembly_type: AssemblyTypeLiteral
    parent_id: str | None = None
    entity_ids: list[str] = Field(default_factory=list)


class IFCTopology(BaseModel):
    """Full node graph + entities + assembly tree for one building assembly."""

    building_id: str
    nodes: dict[str, IFCNode]
    entities: list[IFCEntity]
    assemblies: dict[str, StructuralAssembly]
    entity_assemblies: dict[str, list[str]] = Field(default_factory=dict)

    def entity_ids_in_assembly(self, assembly_id: str) -> list[str]:
        assembly = self.assemblies.get(assembly_id)
        return list(assembly.entity_ids) if assembly else []

    def highlight_entity_ids(self, entity_id: str) -> list[str]:
        """All entity ids to highlight when the user selects one member."""
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if entity is None:
            return [entity_id]
        primary = entity.primary_assembly_id
        ids = self.entity_ids_in_assembly(primary)
        return ids if ids else [entity_id]
