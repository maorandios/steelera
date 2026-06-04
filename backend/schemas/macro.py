from pydantic import BaseModel, Field, model_validator

from schemas.elements import ProjectElementMm
from schemas.project import ProjectState


class GenerateShedRequest(BaseModel):
    assembly_id: str = "shed_1"
    x_spans: list[float] | str = Field(
        ...,
        description='Structural bays across width (mm), e.g. "3000, 7000, 10000, 5000"',
    )
    z_spans: list[float] | str = Field(
        ...,
        description='Portal frame bays along depth (mm), e.g. "5000, 5000, 5000"',
    )
    height: float = Field(..., gt=0, description="Eave / outer column height (mm)")
    roof_pitch_deg: float = Field(10.0, ge=0, lt=90)
    purlin_spacing: float = Field(1200.0, gt=0, description="Purlin spacing along roof slope (mm)")
    replace_existing: bool = Field(
        True,
        description="Remove prior members with the same assembly_id before appending",
    )
    # Legacy optional — derived from spans when omitted
    width: float | None = Field(None, gt=0)
    length: float | None = Field(None, gt=0)
    frame_spacing: float | None = Field(None, gt=0)


class GenerateShedResponse(BaseModel):
    assembly_id: str
    elements: list[dict]
    projectElements: list[ProjectElementMm]
    projectState: ProjectState
    counts: dict[str, int]
