"""Shed engineering proposal — wizard inputs → grid_definition draft."""

from typing import Literal

from pydantic import BaseModel, Field

from schemas.site import SiteContext, SiteSurroundingsLiteral, StructuralRecommendations
from schemas.spatial_grid import GridDefinition

ExposureLiteral = Literal["open", "sheltered"]
RoofStyleLiteral = Literal["duo_pitch", "mono_pitch", "flat"]


class ShedProposalRequest(BaseModel):
    use_case: str = Field("", description="Free-text use case, e.g. warehouse, workshop.")
    width_mm: float = Field(..., gt=0)
    length_mm: float = Field(..., gt=0)
    height_mm: float = Field(6000.0, gt=0)
    roof_style: RoofStyleLiteral = "duo_pitch"
    roof_pitch_deg: float = Field(10.0, ge=0, lt=90)
    latitude: float | None = Field(None, description="Site latitude (WGS84).")
    longitude: float | None = Field(None, description="Site longitude (WGS84).")
    location_label: str = Field("", description="Human-readable site label.")
    site_surroundings: SiteSurroundingsLiteral = Field(
        "auto",
        description="User surroundings override from onboarding refine step.",
    )
    exposure: ExposureLiteral | None = Field(
        None,
        description="Override exposure; derived from site data when omitted.",
    )
    bay_spacing_mm: float | None = Field(
        None,
        gt=0,
        description="Portal frame spacing along length; null = auto from site loads.",
    )


TierLiteral = Literal["light", "recommended", "conservative"]


class SectionTierPackage(BaseModel):
    tier: TierLiteral
    column_profile: str
    column_utilization: float | None = None
    truss_chord_profile: str | None = None
    chord_utilization: float | None = None
    truss_web_profile: str | None = None
    web_utilization: float | None = None
    tie_beam_profile: str = "IPE200"
    tie_beam_utilization: float | None = None
    bracing_profile: str = "L50x50"
    bracing_utilization: float | None = None


class AiProposalReview(BaseModel):
    narrative: str = ""
    recommended_tier: TierLiteral = "recommended"
    comparison_summary: str = ""
    concerns: list[str] = Field(default_factory=list)
    ai_available: bool = False


class ShedProposalResponse(BaseModel):
    grid_definition: GridDefinition
    rationale: list[str] = Field(default_factory=list)
    summary: str = ""
    site_context: SiteContext | None = None
    recommendations: StructuralRecommendations | None = None
    section_tiers: list[SectionTierPackage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ai_review: AiProposalReview | None = None
    active_tier: TierLiteral = "recommended"
