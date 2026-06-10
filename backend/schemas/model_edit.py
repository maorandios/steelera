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


class ModelEditBody(BaseModel):
    project_elements: list[ProjectElementMm] = Field(default_factory=list)
