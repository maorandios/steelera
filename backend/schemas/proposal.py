"""Shed engineering proposal — wizard inputs → grid_definition draft."""

from typing import Literal

from pydantic import BaseModel, Field

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
    exposure: ExposureLiteral = "open"
    bay_spacing_mm: float | None = Field(
        None,
        gt=0,
        description="Portal frame spacing along length; null = auto (6000 mm).",
    )


class ShedProposalResponse(BaseModel):
    grid_definition: GridDefinition
    rationale: list[str] = Field(default_factory=list)
    summary: str = ""
