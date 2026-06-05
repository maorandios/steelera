"""AI-authored structural bill of materials (explicit 3D nodes, mm)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

StructuralElementType = Literal[
    "column",
    "rafter",
    "truss_chord",
    "truss_web",
    "purlin",
    "wall_girt",
    "x_brace",
    "sag_rod",
    "tie_beam",
    "bracing",
]

BomProfileName = Literal[
    "HEA200",
    "IPE200",
    "IPE300",
    "C150",
    "L50x50",
    "ROD12",
]


class StructuralBomMember(BaseModel):
    """One member with explicit start/end nodes (backend coords: Y vertical)."""

    element_type: StructuralElementType
    profile: BomProfileName
    start_node: list[float] = Field(min_length=3, max_length=3)
    end_node: list[float] = Field(min_length=3, max_length=3)
    rotation_deg: float = 0.0

    @field_validator("start_node", "end_node")
    @classmethod
    def finite_nodes(cls, value: list[float]) -> list[float]:
        coords = [float(v) for v in value]
        if not all(abs(v) < 1e9 for v in coords):
            raise ValueError("node coordinates must be finite")
        return coords


class SubmitStructuralLayoutInput(BaseModel):
    """Full structural layout from the AI engineering engine."""

    assembly_id: str = "shed_1"
    replace_existing: bool = True
    elements: list[StructuralBomMember] = Field(min_length=1)

    @field_validator("assembly_id")
    @classmethod
    def normalize_assembly(cls, value: str) -> str:
        key = str(value).strip() or "shed_1"
        return key
