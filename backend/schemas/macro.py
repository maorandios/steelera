from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.elements import ProjectElementMm
from schemas.project import ProjectState


class ShedRoofStyle(str, Enum):
    DUO_PITCH = "duo_pitch"
    MONO_PITCH = "mono_pitch"
    FLAT = "flat"


RoofStyleInput = Literal["duo_pitch", "mono_pitch", "flat"]


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
    roof_style: RoofStyleInput = Field(
        "duo_pitch",
        description="duo_pitch (ridge at center), mono_pitch (single slope 0→width), flat (0°)",
    )
    purlin_spacing: float = Field(1200.0, gt=0, description="Purlin spacing along roof slope (mm)")
    girt_spacing_mm: float = Field(
        1500.0,
        gt=0,
        description="Vertical spacing of horizontal wall girts (mm)",
    )
    use_truss: bool = Field(
        False,
        description="Replace solid IPE rafters with a roof truss (chords + web pattern)",
    )
    truss_type: str = Field(
        "pratt",
        description=(
            "Truss web pattern when use_truss=true: pratt | howe | warren | fink | "
            "king_post | queen_post | scissor."
        ),
    )

    @field_validator("truss_type", mode="before")
    @classmethod
    def _normalize_truss_type(cls, value: str | None) -> str:
        from schemas.spatial_grid import _normalize_truss_type_value

        return _normalize_truss_type_value(value, "pratt")
    use_bracing: bool = Field(
        False,
        description="Cross (X) bracing on the LONG side walls",
    )
    use_gable_bracing: bool = Field(
        False,
        description="Cross (X) bracing on the two GABLE END walls",
    )
    use_roof_bracing: bool = Field(
        False,
        description="Cross (X) bracing in the ROOF planes (end bays)",
    )
    use_sag_rods: bool = Field(
        False,
        description="Slender ties between adjacent purlins / girts mid-bay",
    )
    use_haunches: bool = Field(
        False,
        description="Tapered eave (knee) + apex haunches on rafter (portal) frames",
    )
    use_fly_braces: bool = Field(
        False,
        description="Small fly/flange braces restraining rafter inner flange (purlin stays)",
    )
    use_base_plates: bool = Field(
        False,
        description="Steel base plates under every column / gable-post foot",
    )
    use_bottom_chord_restraint: bool = Field(
        False,
        description="Longitudinal runners restraining truss bottom chords between frames",
    )
    generate_wall_girts: bool = Field(
        True,
        description="Horizontal girts along building perimeter at girt_spacing_mm",
    )
    generate_tie_beams: bool = Field(
        True,
        description="Longitudinal tie members at eave and ridge tying portal frames",
    )
    replace_existing: bool = Field(
        True,
        description="Remove prior members with the same assembly_id before appending",
    )
    width: float | None = Field(None, gt=0)
    length: float | None = Field(None, gt=0)
    frame_spacing: float | None = Field(None, gt=0)

    @field_validator("roof_style", mode="before")
    @classmethod
    def normalize_roof_style(cls, value: str | ShedRoofStyle) -> str:
        if isinstance(value, ShedRoofStyle):
            return value.value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        allowed = {"duo_pitch", "mono_pitch", "flat"}
        if key not in allowed:
            raise ValueError(f"roof_style must be one of {sorted(allowed)}")
        return key

    @model_validator(mode="after")
    def validate_flat_roof_pitch(self) -> "GenerateShedRequest":
        if self.roof_style == "flat" and self.roof_pitch_deg > 0.01:
            # Allow pitch value in request but flat forces 0 in geometry.
            pass
        return self


class GenerateShedResponse(BaseModel):
    assembly_id: str
    elements: list[dict]
    projectElements: list[ProjectElementMm]
    projectState: ProjectState
    counts: dict[str, int]
