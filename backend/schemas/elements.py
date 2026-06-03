from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ShapeType = Literal["I-beam", "C-channel", "Box", "Pipe"]
SectionSource = Literal["catalog", "parametric"]
CatalogProfileName = Literal["IPE200", "IPE300", "HEA200"]
ProfileNameInput = Literal["NONE", "IPE200", "IPE300", "HEA200"]
ExtrusionAxis = Literal["x", "y", "z"]
AnchorPointInput = Literal["NONE", "TOP", "BOTTOM", "START", "END", "CENTER"]


class DimensionInput(BaseModel):
    value: float
    unit: Literal["m", "mm", "ft", "in", "auto"] = "auto"


class PositionInput(BaseModel):
    x: float
    y: float
    z: float


class AddStructuralElementInput(BaseModel):
    shape_type: ShapeType
    length: DimensionInput
    width: DimensionInput
    position: PositionInput
    profile_name: ProfileNameInput = "NONE"
    axis: ExtrusionAxis = "y"
    anchor_element_id: str = "NONE"
    anchor_point: AnchorPointInput = "NONE"

    @field_validator("anchor_element_id", mode="before")
    @classmethod
    def normalize_anchor_id(cls, v: str | None) -> str:
        if v is None or str(v).strip().upper() in ("", "NONE", "NULL"):
            return "NONE"
        return str(v).strip()

    @field_validator("anchor_point", mode="before")
    @classmethod
    def normalize_anchor_point(cls, v: str | None) -> str:
        if v is None:
            return "NONE"
        key = str(v).strip().upper()
        return key if key else "NONE"

    @field_validator("profile_name", mode="before")
    @classmethod
    def normalize_profile_name(cls, v: str) -> str:
        if v is None:
            return "NONE"
        key = str(v).strip().upper().replace(" ", "")
        return key if key else "NONE"

    @model_validator(mode="after")
    def validate_section(self) -> "AddStructuralElementInput":
        if self.profile_name != "NONE" and self.shape_type != "I-beam":
            raise ValueError(
                "Catalog profiles (IPE/HEA) require shape_type 'I-beam'"
            )
        if self.uses_anchor() and not self.anchor_point:
            raise ValueError("anchor_point required when anchor_element_id is set")
        if self.anchor_point != "NONE" and not self.uses_anchor():
            raise ValueError("anchor_element_id required when anchor_point is set")
        return self

    def uses_catalog(self) -> bool:
        return self.profile_name != "NONE"

    def uses_anchor(self) -> bool:
        return self.anchor_element_id != "NONE"


class SectionDimensionsMm(BaseModel):
    """Authentic section dims for extruded I-beam rendering."""

    h: float
    b: float
    tw: float
    tf: float


class ProjectElementMm(BaseModel):
    """Millimeter-based element for frontend (box or extruded I-section)."""

    id: str
    shape_type: ShapeType
    position_mm: dict[str, float]
    size_mm: dict[str, float]
    length_mm: float
    width_mm: float
    depth_mm: float
    section_source: SectionSource = "parametric"
    profile_name: str | None = None
    section_mm: SectionDimensionsMm | None = None
    axis: ExtrusionAxis = "y"
    anchor_element_id: str | None = None
    anchor_point: str | None = None
    # Connection nodes in backend coords (Y = vertical / member height).
    # Vertical (axis y): bottom + top. Horizontal (axis x/z): start + end.
    nodes: dict[str, list[float]] = Field(default_factory=dict)
