from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ShapeType = Literal[
    "I-beam", "C-channel", "Box", "Pipe", "Plate", "Haunch",
    "RHS", "CHS", "Angle", "Tee", "Zed"
]
SectionSource = Literal["catalog", "parametric"]
# Any catalog designation is accepted (validated against the loaded catalog at runtime).
CatalogProfileName = str
ProfileNameInput = str
ExtrusionAxis = Literal["x", "y", "z"]
AnchorPointInput = Literal["NONE", "TOP", "BOTTOM", "START", "END", "CENTER"]
MacroActionType = Literal["ARRAY", "DELETE"]
ArrayAxis = Literal["X", "Y", "Z"]


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
        if self.profile_name != "NONE":
            from catalog_loader import has_profile

            if not has_profile(self.profile_name):
                raise ValueError(
                    f"Unknown catalog profile '{self.profile_name}' (see /api/catalog)"
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


class ApplyMacroActionInput(BaseModel):
    target_element_id: str
    action_type: MacroActionType
    count: int | None = None
    spacing: DimensionInput | None = None
    axis: ArrayAxis | None = None

    @field_validator("target_element_id", mode="before")
    @classmethod
    def normalize_target_id(cls, v: str) -> str:
        key = str(v).strip()
        if not key:
            raise ValueError("target_element_id is required")
        return key

    @field_validator("axis", mode="before")
    @classmethod
    def normalize_axis(cls, v: str | None) -> str | None:
        if v is None:
            return None
        key = str(v).strip().upper()
        return key if key else None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ApplyMacroActionInput":
        if self.action_type == "ARRAY":
            if self.count is None or self.count < 1:
                raise ValueError("ARRAY requires count >= 1")
            if self.spacing is None:
                raise ValueError("ARRAY requires spacing")
            if self.axis is None:
                raise ValueError("ARRAY requires axis (X, Y, or Z)")
        return self


class SectionDimensionsMm(BaseModel):
    """Authentic section dims for extruded rendering.

    h/b/tw/tf cover open I/H/U/Tee sections. Optional fields carry hollow and
    angle geometry: ``t`` wall thickness (RHS/SHS/CHS), ``d`` outer diameter (CHS),
    ``ro`` outer corner radius (RHS/SHS), ``r`` root radius (open sections).
    """

    h: float
    b: float
    tw: float
    tf: float
    t: float | None = None
    d: float | None = None
    ro: float | None = None
    r: float | None = None
    lip: float | None = None


ElementAlignment = Literal["center", "top", "bottom"]


class ProjectElementMm(BaseModel):
    """Millimeter-based element for frontend (box or extruded I-section)."""

    id: str
    assembly_id: str | None = None
    shape_type: ShapeType
    position_mm: dict[str, float]
    size_mm: dict[str, float]
    length_mm: float
    width_mm: float
    depth_mm: float
    # Tapered members (e.g. haunches): section depth at the far end (start depth = depth_mm).
    taper_end_depth_mm: float | None = None
    section_source: SectionSource = "parametric"
    profile_name: str | None = None
    section_mm: SectionDimensionsMm | None = None
    axis: ExtrusionAxis = "y"
    alignment: ElementAlignment = "center"
    rotation_euler_deg: list[float] | None = None
    anchor_element_id: str | None = None
    anchor_point: str | None = None
    # Connection nodes in backend coords (Y = vertical / member height).
    # Vertical (axis y): bottom + top. Horizontal (axis x/z): start + end.
    nodes: dict[str, list[float]] = Field(default_factory=dict)
    # Macro / assembly role (column, rafter, wall_girt, bracing, truss_chord, …).
    element_type: str | None = None
    # IFC assembly grouping for sub-assembly selection highlight.
    primary_assembly_id: str | None = None
    assembly_ids: list[str] | None = None
