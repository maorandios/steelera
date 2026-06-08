"""Universal spatial grid — logical node references and uniform structural members."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

RoofStyleLiteral = Literal["duo_pitch", "mono_pitch", "flat"]
TrussTypeLiteral = Literal[
    "pratt",
    "howe",
    "warren",
    "fink",
    "king_post",
    "queen_post",
    "scissor",
    "none",
]

_TRUSS_TYPE_VALUES = {
    "pratt",
    "howe",
    "warren",
    "fink",
    "king_post",
    "queen_post",
    "scissor",
    "none",
}

_TRUSS_TYPE_ALIASES = {
    "kingpost": "king_post",
    "king": "king_post",
    "queenpost": "queen_post",
    "queen": "queen_post",
    "scissors": "scissor",
}


def _normalize_truss_type_value(value: str | None, default: str) -> str:
    if value is None:
        return default
    key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    key = key.removesuffix("_truss")
    key = _TRUSS_TYPE_ALIASES.get(key, key)
    return key if key in _TRUSS_TYPE_VALUES else default

ElevationLiteral = Literal[
    "ground",
    "eave",
    "roof",
    "apex",
    "ridge",
]

StructuralElementType = Literal[
    "column",
    "rafter",
    "truss_chord",
    "truss_web",
    "purlin",
    "wall_girt",
    "tie_beam",
    "bracing",
    "x_brace",
    "sag_rod",
    "haunch",
    "fly_brace",
    "base_plate",
]

# Any catalog designation is accepted (validated against the loaded catalog at runtime).
MemberProfile = str


class GridNodeReference(BaseModel):
    """
    Logical grid address. Axes use letters on X (A, B, …) and numbers on Z (1, 2, …).
    Sub-nodes: ``A+2/5`` = 2/5 of the span from axis A toward the next X line.
    Elevations: ground | eave | roof | apex | ridge, or ``eave+1/4`` between eave and roof at X.
    """

    x_axis: str = Field(..., description='X grid line, e.g. "A" or "A+2/5"')
    z_axis: str = Field(..., description='Z grid line, e.g. "1" or "2+1/3"')
    elevation: str = Field(
        "ground",
        description='Named level or fraction, e.g. "eave", "roof", "apex", "eave+2/5"',
    )
    offset_mm: dict[str, float] = Field(
        default_factory=dict,
        description="Optional clearance offsets applied after grid resolve (x, y, z).",
    )

    @field_validator("x_axis", "z_axis", "elevation")
    @classmethod
    def strip_ref(cls, value: str) -> str:
        return str(value).strip()


class GridDefinition(BaseModel):
    """Inputs to build the 3D node matrix (Python-owned geometry).

    Feature flags express engineering INTENT; Python generates every member.
    """

    x_spans: list[float] = Field(..., min_length=1)
    z_spans: list[float] = Field(..., min_length=1)
    height_mm: float = Field(..., gt=0)
    roof_pitch_deg: float = Field(10.0, ge=0, lt=90)
    roof_style: RoofStyleLiteral = "duo_pitch"
    mono_high_side: Literal["A", "B"] = "B"

    use_truss: bool = False
    truss_type: TrussTypeLiteral = "none"
    x_bracing: bool = False
    gable_bracing: bool = False
    roof_bracing: bool = False
    sag_rods: bool = False
    haunches: bool = False
    fly_braces: bool = False
    base_plates: bool = False
    bottom_chord_restraint: bool = False
    generate_purlins: bool = True
    generate_wall_girts: bool = True
    generate_tie_beams: bool = True
    purlin_spacing_mm: float = Field(1200.0, gt=0)
    girt_spacing_mm: float = Field(1500.0, gt=0)
    column_profile: str | None = Field(
        None, description="Catalog column section (e.g. HEA200 / SHS300x300x10)."
    )
    bracing_profile: str | None = Field(
        None, description="Catalog bracing angle (e.g. L50x50 / L100x100x10)."
    )
    purlin_profile: str | None = Field(
        None, description="Catalog purlin section (e.g. C200x2.0 / Z200x2.0)."
    )
    girt_profile: str | None = Field(
        None, description="Catalog girt section (e.g. C150x2.0 / Z150x2.0)."
    )
    sag_rod_profile: str | None = Field(
        None, description="Catalog sag/tie rod (e.g. ROD12 / ROD16)."
    )
    base_plate_profile: str | None = Field(
        None, description="Catalog base plate thickness (e.g. PL12 / PL20)."
    )
    truss_chord_profile: str | None = Field(
        None,
        description="Truss top + bottom chord section (e.g. SHS120x120x6 / IPE200).",
    )
    truss_web_profile: str | None = Field(
        None,
        description="Truss web diagonal section (e.g. L60x60x6 / L50x50).",
    )
    custom_levels: dict[str, float] = Field(
        default_factory=dict,
        description="AI-defined named elevation levels in mm (e.g. {'mezzanine': 3500}). "
        "Server-populated from define_level operations; resolvable like built-in elevations.",
    )

    @field_validator("x_spans", "z_spans")
    @classmethod
    def positive_spans(cls, spans: list[float]) -> list[float]:
        out = [float(s) for s in spans]
        if any(s <= 0 for s in out):
            raise ValueError("all span values must be positive")
        return out

    @field_validator(
        "column_profile",
        "bracing_profile",
        "purlin_profile",
        "girt_profile",
        "sag_rod_profile",
        "base_plate_profile",
        "truss_chord_profile",
        "truss_web_profile",
    )
    @classmethod
    def validate_profile(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = str(value).strip()
        if not name:
            return None
        from catalog_loader import has_profile

        if not has_profile(name):
            raise ValueError(f"unknown catalog profile '{name}'")
        return name

    @field_validator("truss_type", mode="before")
    @classmethod
    def normalize_truss_type(cls, value: str | None) -> str:
        return _normalize_truss_type_value(value, "none")


class StructuralMember(BaseModel):
    """One member defined only by grid-snapped start/end nodes."""

    id: str
    element_type: StructuralElementType
    profile: MemberProfile
    start_node: GridNodeReference
    end_node: GridNodeReference
    alignment: Literal["center", "start", "end"] = "center"

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        key = str(value).strip()
        if not key:
            raise ValueError("member id is required")
        return key

    @field_validator("profile")
    @classmethod
    def validate_profile(cls, value: str) -> str:
        name = str(value).strip()
        if not name:
            raise ValueError("member profile is required")
        from catalog_loader import has_profile

        if not has_profile(name):
            raise ValueError(f"unknown catalog profile '{name}'")
        return name


class StructuralGridLayout(BaseModel):
    """Full layout: grid definition + uniform member BOM for the resolver."""

    assembly_id: str = "shed_1"
    replace_existing: bool = True
    grid_definition: GridDefinition
    structural_members: list[StructuralMember] = Field(
        default_factory=list,
        description="If empty, Python auto-generates a standard portal frame on the grid.",
    )

    @field_validator("assembly_id")
    @classmethod
    def normalize_assembly(cls, value: str) -> str:
        return str(value).strip() or "shed_1"
