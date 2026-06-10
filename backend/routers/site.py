from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from core.site_context import geocode_address, resolve_site_context
from schemas.site import GeocodeResult, SiteContext, SiteSurroundingsLiteral

router = APIRouter(prefix="/api/site", tags=["site"])


@router.get("/context", response_model=SiteContext)
async def site_context(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    label: str = Query("", description="Optional display label for the site."),
    surroundings: SiteSurroundingsLiteral = Query(
        "auto",
        description="User override: built_up, open_industrial, or auto from map data.",
    ),
) -> SiteContext:
    try:
        return resolve_site_context(
            lat,
            lon,
            location_label=label,
            surroundings=surroundings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Site data unavailable: {exc}") from exc


@router.get("/geocode", response_model=GeocodeResult)
async def geocode(q: str = Query(..., min_length=2)) -> GeocodeResult:
    try:
        return geocode_address(q)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {exc}") from exc
