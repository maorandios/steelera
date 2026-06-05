"""Parametric shed assembly — AI coordinates layout flags; Python computes geometry."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.spatial_grid import TrussTypeLiteral, _normalize_truss_type_value

RoofStyleLiteral = Literal["duo_pitch", "mono_pitch", "flat"]


class ShedGlobalParameters(BaseModel):
    height_mm: float = Field(..., gt=0, description="Eave height (mm)")
    roof_pitch_deg: float = Field(10.0, ge=0, lt=90)
    roof_style: RoofStyleLiteral = "duo_pitch"

    @field_validator("roof_style", mode="before")
    @classmethod
    def normalize_roof_style(cls, value: str | None) -> str:
        if value is None:
            return "duo_pitch"
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if key in ("duo_pitch", "mono_pitch", "flat"):
            return key
        raise ValueError("roof_style must be duo_pitch, mono_pitch, or flat")


class ShedGridLayout(BaseModel):
    x_spans: list[float] = Field(
        ...,
        min_length=1,
        description="Bay widths across X in mm (sum = building width)",
    )
    z_spans: list[float] = Field(
        ...,
        min_length=1,
        description="Portal-frame bay spacings along Z in mm (sum = building length)",
    )

    @field_validator("x_spans", "z_spans")
    @classmethod
    def positive_spans(cls, spans: list[float]) -> list[float]:
        out = [float(s) for s in spans]
        if any(s <= 0 for s in out):
            raise ValueError("all span values must be positive")
        return out


class ShedBayConfiguration(BaseModel):
    """Per longitudinal Z-bay (between frame bay_index and bay_index+1)."""

    bay_index: int = Field(..., ge=0)
    use_truss: bool = False
    truss_type: TrussTypeLiteral = "pratt"
    x_bracing_left_wall: bool = False
    x_bracing_right_wall: bool = False
    wall_girts: bool = True
    sag_rods: bool = False

    @field_validator("truss_type", mode="before")
    @classmethod
    def normalize_truss_type(cls, value: str | None) -> str:
        return _normalize_truss_type_value(value, "pratt")


class ShedAssemblyConfig(BaseModel):
    """Unified parametric config for generate_shed_macro (Python-owned geometry)."""

    assembly_id: str = "shed_1"
    replace_existing: bool = True
    global_parameters: ShedGlobalParameters
    grid_layout: ShedGridLayout
    bays_configuration: list[ShedBayConfiguration] = Field(default_factory=list)
    mono_high_side: Literal["A", "B"] = "B"
    purlin_spacing_mm: float = Field(1200.0, gt=0)
    girt_spacing_mm: float = Field(1500.0, gt=0)
    generate_tie_beams: bool = True
    gable_bracing: bool = False
    roof_bracing: bool = False
    haunches: bool = False
    fly_braces: bool = False
    base_plates: bool = False
    bottom_chord_restraint: bool = False

    @model_validator(mode="after")
    def validate_bay_indices(self) -> "ShedAssemblyConfig":
        n_bays = len(self.grid_layout.z_spans)
        seen: set[int] = set()
        for bay in self.bays_configuration:
            if bay.bay_index < 0 or bay.bay_index >= n_bays:
                raise ValueError(
                    f"bay_index {bay.bay_index} out of range 0..{n_bays - 1}"
                )
            if bay.bay_index in seen:
                raise ValueError(f"duplicate bay_index {bay.bay_index}")
            seen.add(bay.bay_index)
        return self

    def with_default_bays(self) -> "ShedAssemblyConfig":
        """Ensure one entry per longitudinal Z-bay (fill omitted indices)."""
        n_bays = len(self.grid_layout.z_spans)
        merged = [self.bay_at(i) for i in range(n_bays)]
        return self.model_copy(update={"bays_configuration": merged})

    def bay_at(self, index: int) -> ShedBayConfiguration:
        """Resolved config for bay index (defaults if omitted)."""
        for bay in self.bays_configuration:
            if bay.bay_index == index:
                if not bay.use_truss:
                    return bay.model_copy(update={"truss_type": "none"})
                return bay
        return ShedBayConfiguration(
            bay_index=index,
            use_truss=False,
            truss_type="none",
            x_bracing_left_wall=False,
            x_bracing_right_wall=False,
            wall_girts=True,
            sag_rods=False,
        )

    def frame_uses_truss(self, frame_index: int) -> tuple[bool, TrussTypeLiteral]:
        """Truss at portal frame line: enabled if either adjacent bay requests it."""
        n_bays = len(self.grid_layout.z_spans)
        n_frames = n_bays + 1
        if frame_index < 0 or frame_index >= n_frames:
            return False, "none"
        types: list[TrussTypeLiteral] = []
        if frame_index > 0:
            b = self.bay_at(frame_index - 1)
            if b.use_truss and b.truss_type != "none":
                types.append(b.truss_type)
        if frame_index < n_bays:
            b = self.bay_at(frame_index)
            if b.use_truss and b.truss_type != "none":
                types.append(b.truss_type)
        if not types:
            return False, "none"
        return True, types[0]
