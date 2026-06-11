"""Sketch-mode AI analysis request/response models."""

from typing import Literal

from pydantic import BaseModel, Field

from schemas.elements import ProjectElementMm
from schemas.site import SiteContext

StructuralIntentKind = Literal[
    "tie_beam", "bracing", "purlin", "beam", "unknown"
]
SketchApplyScope = Literal["all_bays", "row", "single"]
AngleClass = Literal["horizontal", "vertical", "diagonal"]
ProfileTier = Literal["light", "recommended", "conservative"]
SnapNodeTier = Literal["primary", "secondary"]


class SketchSnapNode(BaseModel):
    x: float
    y: float
    z: float
    element_id: str
    element_type: str
    tier: SnapNodeTier = "primary"
    param_along_member: float = 0.0


class SketchAnalyzeRequest(BaseModel):
    project_elements: list[ProjectElementMm] = Field(default_factory=list)
    start_node: SketchSnapNode
    end_node: SketchSnapNode
    intent_override: StructuralIntentKind | None = None
    site_context: SiteContext | None = None
    shed_params: dict | None = None
    x_coords_mm: list[float] | None = None
    z_coords_mm: list[float] | None = None


class SketchIntentResult(BaseModel):
    kind: StructuralIntentKind
    confidence: float
    label: str
    angle_class: AngleClass
    span_mm: float
    start_element_type: str
    end_element_type: str
    start_element_id: str
    end_element_id: str


class SketchProfileOption(BaseModel):
    profile: str
    tier: ProfileTier
    tier_label: str
    utilization: float
    governing: str


class SketchAnalyzeResponse(BaseModel):
    intent: SketchIntentResult
    profiles: list[SketchProfileOption]
    message: str
    scope_suggestion: SketchApplyScope
    scope_reason: str
    alternatives: list[StructuralIntentKind] = Field(default_factory=list)
    ai_available: bool = False
