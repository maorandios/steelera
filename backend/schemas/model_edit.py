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


class PlaceBracingCrossRequest(BaseModel):
    """Two diagonals: start_a→end_a and start_b→end_b."""
    start_a_mm: Point3Mm
    end_a_mm: Point3Mm
    start_b_mm: Point3Mm
    end_b_mm: Point3Mm
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
    assembly_id: str | None = None
    grid: GridPlacementContext
    trussed_z_labels: list[str] = Field(default_factory=list)


class PlaceGridTieBeamRequest(BaseModel):
    x_axis: str
    z_start: str = Field(..., description='Start frame e.g. "2"')
    z_end: str = Field(..., description='End frame e.g. "3"')
    profile: str = Field(default="IPE200")
    elevation: str = Field(default="eave", description="eave | roof | apex")
    assembly_id: str | None = None
    grid: GridPlacementContext


class ModelEditBody(BaseModel):
    project_elements: list[ProjectElementMm] = Field(default_factory=list)
