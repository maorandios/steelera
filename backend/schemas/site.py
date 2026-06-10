"""Site context from open geospatial / climate data."""

from typing import Literal

from pydantic import BaseModel, Field

TerrainClassLiteral = Literal["0", "II", "III", "IV"]
ExposureLiteral = Literal["open", "sheltered"]
SiteSurroundingsLiteral = Literal["auto", "built_up", "open_industrial"]


class SiteContext(BaseModel):
    latitude: float
    longitude: float
    location_label: str = ""
    mean_wind_ms: float = Field(description="Long-term mean wind speed at 10 m (m/s).")
    design_wind_proxy_ms: float = Field(
        description=(
            "Internal exposure proxy from open climate data (m/s). "
            "Not a code design wind speed (e.g. IS 413 / EC1)."
        ),
    )
    terrain_class: TerrainClassLiteral = "III"
    exposure: ExposureLiteral = "open"
    load_index: float = Field(
        description="Internal Steelera load index for preliminary sizing heuristics."
    )
    building_count_500m: int = 0
    near_water: bool = False
    data_sources: list[str] = Field(default_factory=list)
    detected_terrain_class: TerrainClassLiteral | None = Field(
        None,
        description="Map-detected terrain before user surroundings override.",
    )
    detected_load_index: float | None = Field(
        None,
        description="Load index from map detection before override.",
    )
    surroundings_applied: SiteSurroundingsLiteral = Field(
        "auto",
        description="Surroundings setting used for this context (auto / built_up / open_industrial).",
    )


class GeocodeResult(BaseModel):
    latitude: float
    longitude: float
    display_name: str = ""


class StructuralRecommendations(BaseModel):
    bay_spacing_mm: float
    use_truss: bool
    truss_type: str
    column_profile: str
    truss_chord_profile: str | None = None
    truss_web_profile: str | None = None
    x_bracing: bool
    roof_bracing: bool
    gable_bracing: bool
    sag_rods: bool
    fly_braces: bool
    haunches: bool
