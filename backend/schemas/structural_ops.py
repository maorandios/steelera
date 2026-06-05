"""
Universal structural operation vocabulary.

The AI composes a small set of element-AGNOSTIC operations; Python expands them
deterministically into uniform StructuralMembers. No operation encodes a specific
element type (shed/roof/mezzanine) — only generic geometric/topological combinators.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from schemas.spatial_grid import (
    GridDefinition,
    GridNodeReference,
    MemberProfile,
    StructuralElementType,
)

# Sentinel inside x_lines/z_lines/at_lines meaning "every grid line on that axis".
ALL = "*"


class DefineLevelOp(BaseModel):
    """Declare a named elevation level (mm). Enables any vertical structure."""

    kind: Literal["define_level"]
    name: str = Field(..., description='Level name, e.g. "mezzanine".')
    height_mm: float = Field(..., description="Absolute height above ground in mm.")


class PlaceMemberOp(BaseModel):
    """One explicit member between two grid nodes."""

    kind: Literal["place_member"]
    id: str
    element_type: StructuralElementType
    profile: MemberProfile
    start_node: GridNodeReference
    end_node: GridNodeReference


class ArrayMemberOp(BaseModel):
    """
    Repeat one template member across grid lines (Cartesian over x_lines × z_lines).

    For each chosen line the matching coordinate is replaced on BOTH endpoints:
    - x_lines replaces x_axis on start and end (keep z from template)
    - z_lines replaces z_axis on start and end (keep x from template)
    Empty list = keep the template's value on that axis. ["*"] = every line on that axis.

    Columns: template A/1/ground→A/1/eave, x_lines=["*"], z_lines=["*"].
    Rafters: template A/1/eave→B/1/roof, x_lines=[], z_lines=["*"].
    """

    kind: Literal["array_member"]
    id_prefix: str
    element_type: StructuralElementType
    profile: MemberProfile
    start_node: GridNodeReference
    end_node: GridNodeReference
    x_lines: list[str] = Field(default_factory=list)
    z_lines: list[str] = Field(default_factory=list)


class ArrayAdjacentOp(BaseModel):
    """
    Connect CONSECUTIVE grid lines along `axis`, repeated at each `at_lines` value
    on the other axis. Use for longitudinal beams that span bay-to-bay
    (tie beams, eave beams, purlins, girts).

    Tie beams along length at both walls:
      axis="z", at_lines=["A","B"], elevation_start="eave", elevation_end="eave".
    """

    kind: Literal["array_adjacent"]
    id_prefix: str
    element_type: StructuralElementType
    profile: MemberProfile
    axis: Literal["x", "z"]
    at_lines: list[str]
    elevation_start: str = "eave"
    elevation_end: str = "eave"


Operation = Annotated[
    Union[DefineLevelOp, PlaceMemberOp, ArrayMemberOp, ArrayAdjacentOp],
    Field(discriminator="kind"),
]


class StructuralDesign(BaseModel):
    """Full design: grid + ordered universal operations (Python expands to members)."""

    assembly_id: str = "shed_1"
    replace_existing: bool = True
    grid_definition: GridDefinition
    operations: list[Operation] = Field(default_factory=list)
