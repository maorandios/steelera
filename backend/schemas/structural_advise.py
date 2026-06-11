"""Unified structural advisory — operation proposals for sketch and selection."""

from typing import Literal

from pydantic import BaseModel, Field

from schemas.chat import SelectionContextPayload
from schemas.elements import ProjectElementMm
from schemas.site import SiteContext
from schemas.sketch import (
    SketchApplyScope,
    SketchIntentResult,
    SketchProfileOption,
    SketchSnapNode,
    StructuralIntentKind,
)

OperationKind = Literal[
    "place_single_member",
    "place_x_brace",
    "place_multi_panel_x",
    "place_member_array",
    "change_profile",
    "change_truss_type",
    "switch_to_truss",
    "switch_to_rafter",
]

BracingPlane = Literal["roof", "wall_long", "gable", "unknown"]


class Point3Mm(BaseModel):
    x: float
    y: float
    z: float


class OperationProposal(BaseModel):
    id: str
    kind: OperationKind
    label: str
    description: str
    recommended: bool = False
    element_kind: StructuralIntentKind | str = "unknown"
    scope_suggestion: SketchApplyScope = "single"
    warnings: list[str] = Field(default_factory=list)
    bracing_plane: BracingPlane | None = None
    panel_count: int | None = None
    """One sketched leg — used to infer full X geometry."""
    leg_start_mm: Point3Mm | None = None
    leg_end_mm: Point3Mm | None = None
    """Explicit X-brace corners when known (a→b and c→d)."""
    x_corners_mm: list[Point3Mm] | None = None
    profile_suggestions: list[SketchProfileOption] = Field(default_factory=list)


class StructuralAdviseRequest(BaseModel):
    trigger: Literal["sketch", "selection"] = "sketch"
    project_elements: list[ProjectElementMm] = Field(default_factory=list)
    start_node: SketchSnapNode | None = None
    end_node: SketchSnapNode | None = None
    selection_context: SelectionContextPayload | None = None
    intent_override: StructuralIntentKind | None = None
    site_context: SiteContext | None = None
    shed_params: dict | None = None
    x_coords_mm: list[float] | None = None
    z_coords_mm: list[float] | None = None


class StructuralAdviseResponse(BaseModel):
    summary: str
    intent: SketchIntentResult | None = None
    operations: list[OperationProposal] = Field(default_factory=list)
    recommended_operation_id: str | None = None
    profiles: list[SketchProfileOption] = Field(default_factory=list)
    scope_suggestion: SketchApplyScope = "single"
    scope_reason: str = ""
    alternatives: list[StructuralIntentKind] = Field(default_factory=list)
    ai_available: bool = False
