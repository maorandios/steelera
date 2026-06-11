"""Surgical model edit requests — profile updates, deletes, bracing placement."""

from typing import Literal

from pydantic import BaseModel, Field

from schemas.elements import ProjectElementMm


class Point3Mm(BaseModel):
    x: float
    y: float
    z: float


class UpdateProfileRequest(BaseModel):
    profile: str = Field(..., description="Catalog designation e.g. L100x100x10")
    element_ids: list[str] = Field(default_factory=list)
    scope: Literal[
        "selection", "pair", "group", "element_type", "frame", "truss"
    ] = "selection"
    reference_element_id: str | None = None


class DeleteMembersRequest(BaseModel):
    element_ids: list[str] = Field(default_factory=list)
    scope: Literal["selection", "pair", "group"] = "selection"
    reference_element_id: str | None = None


class PlaceBraceLegRequest(BaseModel):
    start_mm: Point3Mm
    end_mm: Point3Mm
    profile: str | None = None
    assembly_id: str | None = None


class PlaceMemberBetweenPointsRequest(BaseModel):
    start_mm: Point3Mm
    end_mm: Point3Mm
    profile: str | None = None
    assembly_id: str | None = None
    element_type: Literal[
        "bracing",
        "tie_beam",
        "purlin",
        "beam",
    ] = "bracing"


class PlaceBracingCrossRequest(BaseModel):
    """Two diagonals: start_a→end_a and start_b→end_b."""
    start_a_mm: Point3Mm
    end_a_mm: Point3Mm
    start_b_mm: Point3Mm
    end_b_mm: Point3Mm
    profile: str | None = None
    assembly_id: str | None = None


class PlaceXBraceFromLegRequest(BaseModel):
    """Infer complementary diagonal and place a full X from one sketched leg."""
    start_mm: Point3Mm
    end_mm: Point3Mm
    start_element_id: str | None = None
    end_element_id: str | None = None
    profile: str | None = None
    assembly_id: str | None = None


class ModelEditResponse(BaseModel):
    projectElements: list[ProjectElementMm]
    message: str
    changed_ids: list[str] = Field(default_factory=list)


class GridPlacementContext(BaseModel):
    """Minimal grid definition to resolve node coordinates for surgical placement."""

    x_spans: list[float] = Field(..., min_length=1)
    z_spans: list[float] = Field(..., min_length=1)
    height_mm: float = Field(..., gt=0)
    roof_pitch_deg: float = Field(10.0, ge=0, lt=90)
    roof_style: str = "duo_pitch"
    mono_high_side: str = "B"


class PlaceGridColumnRequest(BaseModel):
    x_axis: str = Field(..., description='X grid line e.g. "A"')
    z_axis: str = Field(..., description='Z grid line or sub-node e.g. "2" or "2+1/2"')
    profile: str = Field(..., description="Catalog column section e.g. HEA200")
    offset_mm: dict[str, float] = Field(default_factory=dict)
    connect_to: Literal["auto", "truss_bc", "eave"] = "auto"
    truss_type: str = "pratt"
    add_tie_in_bay: bool = False
    tie_profile: str | None = None
    bay_z_start: str | None = None
    bay_z_end: str | None = None
    assembly_id: str | None = None
    grid: GridPlacementContext
    trussed_z_labels: list[str] = Field(default_factory=list)


class GroundPlacementNodesRequest(BaseModel):
    grid: GridPlacementContext
    trussed_z_labels: list[str] = Field(default_factory=list)
    truss_type: str = "pratt"
    bay_z_start: str | None = None
    bay_z_end: str | None = None
    extra_wall_offsets_mm: list[float] = Field(default_factory=list)


class PlaceGridTieBeamRequest(BaseModel):
    orientation: Literal["along_z", "along_x"] = Field(
        default="along_z",
        description="along_z: tie on a wall/truss X line between frames; along_x: gable tie along X at fixed Z.",
    )
    x_axis: str = Field(default="", description='Wall/truss grid line for along_z ties e.g. "A".')
    z_start: str = Field(default="", description='Start frame for along_z e.g. "2".')
    z_end: str = Field(default="", description='End frame for along_z e.g. "3".')
    z_axis: str | None = Field(
        default=None,
        description='Gable frame line for along_x ties e.g. "1".',
    )
    x_start: str | None = Field(
        default=None,
        description='Gable tie start X line for along_x.',
    )
    x_end: str | None = Field(
        default=None,
        description='Gable tie end X line for along_x.',
    )
    profile: str = Field(default="IPE200")
    elevation: str = Field(default="eave", description="eave | roof | apex")
    placement_label: str | None = Field(
        default=None,
        description="Optional disambiguator for multiple ties in one bay (e.g. start, middle).",
    )
    assembly_id: str | None = None
    grid: GridPlacementContext


class PlaceWallXBraceRequest(BaseModel):
    """Full X-brace in a wall panel — long side wall, gable end wall, or roof slope."""

    panel_kind: Literal["long_wall", "gable_wall", "roof"] = "long_wall"
    wall_x: str = Field(
        ...,
        description='Long wall: grid line e.g. "A". Gable/roof: X-bay start line e.g. "A".',
    )
    bay_index: int = Field(
        ...,
        ge=0,
        description="Long wall: zero-based Z bay. Gable: zero-based X bay.",
    )
    frame_z: str | None = Field(
        default=None,
        description='Gable end frame e.g. "1" (required when panel_kind is gable_wall).',
    )
    z_start: str | None = Field(
        default=None,
        description="Long-wall bay start frame (overrides bay_index lookup).",
    )
    z_end: str | None = Field(
        default=None,
        description="Long-wall bay end frame (overrides bay_index lookup).",
    )
    x_start: str | None = Field(
        default=None,
        description="Gable panel start grid line (overrides X bay lookup).",
    )
    x_end: str | None = Field(
        default=None,
        description="Gable/roof panel end grid line (overrides X bay lookup).",
    )
    elev_start: str | None = Field(
        default=None,
        description='Roof slope start elevation e.g. "eave" or "apex".',
    )
    elev_end: str | None = Field(
        default=None,
        description='Roof slope end elevation e.g. "eave" or "apex".',
    )
    slope_side: Literal["left", "right", "mono"] | None = Field(
        default=None,
        description="Roof slope side for scoped placement.",
    )
    brace_count: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Stacked X-brace pairs per panel (1–5).",
    )
    profile: str | None = None
    assembly_id: str | None = None
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel"
    grid: GridPlacementContext


class ModelEditBody(BaseModel):
    project_elements: list[ProjectElementMm] = Field(default_factory=list)
