"""Fetch site wind and terrain context from free open-data APIs."""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any

from schemas.site import GeocodeResult, SiteContext

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_USER_AGENT = "Steelera/1.0 (structural-design; contact=dev@steelera.local)"


def _http_get_json(url: str, *, timeout: float = 30.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode_address(query: str) -> GeocodeResult:
    """Resolve a free-text address or place name to coordinates."""
    q = query.strip()
    if not q:
        raise ValueError("Location query is empty")
    params = urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": "1"},
    )
    data = _http_get_json(f"{_NOMINATIM_URL}?{params}", timeout=20.0)
    if not data:
        raise ValueError(f"Could not find location: {q}")
    hit = data[0]
    return GeocodeResult(
        latitude=float(hit["lat"]),
        longitude=float(hit["lon"]),
        display_name=str(hit.get("display_name", q)),
    )


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil(pct / 100.0 * len(ordered)) - 1)))
    return ordered[idx]


def _fetch_wind_stats(lat: float, lon: float) -> tuple[float, float, str]:
    """Return (mean_ms, p95_ms, source_label)."""
    end_year = date.today().year - 1
    start_year = max(end_year - 4, 2010)
    params = urllib.parse.urlencode(
        {
            "latitude": f"{lat:.5f}",
            "longitude": f"{lon:.5f}",
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            # Daily maxima: ~1.8k points vs ~44k hourly — much faster to download.
            "daily": "wind_speed_10m_max",
            "wind_speed_unit": "ms",
        },
    )
    try:
        data = _http_get_json(f"{_OPEN_METEO_ARCHIVE}?{params}", timeout=28.0)
        speeds = [
            float(v)
            for v in data.get("daily", {}).get("wind_speed_10m_max", [])
            if v is not None
        ]
        if not speeds:
            raise ValueError("no wind samples")
        mean = sum(speeds) / len(speeds)
        p95 = _percentile(speeds, 95)
        return mean, p95, "open-meteo-era5-daily"
    except Exception:
        return 6.0, 9.0, "default-fallback"


def _overpass_count(query: str) -> int:
    try:
        payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(
            _OVERPASS_URL,
            data=payload,
            headers={"User-Agent": _USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elements = data.get("elements", [])
        for el in elements:
            if el.get("type") == "count":
                return int(el.get("tags", {}).get("ways", 0))
        return len([e for e in elements if e.get("type") == "way"])
    except Exception:
        return 0


def _terrain_from_osm(lat: float, lon: float) -> tuple[str, int, bool, str]:
    """Return (terrain_class, building_count, near_water, source)."""
    building_q = f"""
[out:json][timeout:20];
way["building"](around:500,{lat},{lon});
out count;
"""
    water_q = f"""
[out:json][timeout:20];
way["natural"="water"](around:400,{lat},{lon});
relation["natural"="water"](around:400,{lat},{lon});
out count;
"""
    with ThreadPoolExecutor(max_workers=2) as pool:
        building_future = pool.submit(_overpass_count, building_q)
        water_future = pool.submit(_overpass_count, water_q)
        buildings = building_future.result()
        water_hits = water_future.result()
    near_water = water_hits > 0

    if near_water and buildings < 8:
        terrain = "0"
    elif buildings < 5:
        terrain = "II"
    elif buildings < 35:
        terrain = "III"
    else:
        terrain = "IV"

    return terrain, buildings, near_water, "openstreetmap-overpass"


def _design_wind_proxy(mean_ms: float, p95_ms: float) -> float:
    return round(max(mean_ms * 1.35, p95_ms * 0.9, 5.0), 2)


def _terrain_load_factor(terrain_class: str, near_water: bool) -> float:
    factors = {"0": 1.25, "II": 1.12, "III": 1.0, "IV": 0.92}
    base = factors.get(terrain_class, 1.0)
    if near_water and terrain_class != "IV":
        base = max(base, 1.15)
    return base


def _exposure_from_terrain(terrain_class: str, load_index: float) -> str:
    if terrain_class in ("0", "II") or load_index >= 10.5:
        return "open"
    return "sheltered"


def apply_surroundings_override(
    ctx: SiteContext,
    surroundings: str,
) -> SiteContext:
    """Adjust terrain/exposure when the user knows the plot better than city centroid."""
    if surroundings == "auto":
        return ctx.model_copy(update={"surroundings_applied": "auto"})

    detected_terrain = ctx.terrain_class
    detected_load = ctx.load_index
    sources = list(ctx.data_sources)
    if surroundings == "open_industrial":
        terrain = "II"
        exposure = "open"
        sources.append("override:open_industrial")
    elif surroundings == "built_up":
        terrain = "IV" if ctx.building_count_500m >= 12 else "III"
        exposure = "sheltered"
        sources.append("override:built_up")
    else:
        return ctx

    load_factor = _terrain_load_factor(terrain, ctx.near_water)
    load_index = round(ctx.design_wind_proxy_ms * load_factor, 2)
    if surroundings == "open_industrial" and load_index < 9.0:
        load_index = max(load_index, 9.0)

    return ctx.model_copy(
        update={
            "terrain_class": terrain,
            "exposure": exposure,
            "load_index": load_index,
            "data_sources": sources,
            "detected_terrain_class": detected_terrain,
            "detected_load_index": detected_load,
            "surroundings_applied": surroundings,
        },
    )


def resolve_site_context(
    lat: float,
    lon: float,
    *,
    location_label: str = "",
    surroundings: str = "auto",
) -> SiteContext:
    """Build site context for structural sizing heuristics."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        wind_future = pool.submit(_fetch_wind_stats, lat, lon)
        terrain_future = pool.submit(_terrain_from_osm, lat, lon)
        mean_ms, p95_ms, wind_src = wind_future.result()
        terrain, buildings, near_water, terrain_src = terrain_future.result()
    design_ms = _design_wind_proxy(mean_ms, p95_ms)
    load_factor = _terrain_load_factor(terrain, near_water)
    load_index = round(design_ms * load_factor, 2)
    exposure = _exposure_from_terrain(terrain, load_index)

    ctx = SiteContext(
        latitude=lat,
        longitude=lon,
        location_label=location_label,
        mean_wind_ms=round(mean_ms, 2),
        design_wind_proxy_ms=design_ms,
        terrain_class=terrain,
        exposure=exposure,
        load_index=load_index,
        building_count_500m=buildings,
        near_water=near_water,
        data_sources=[wind_src, terrain_src],
    )
    return apply_surroundings_override(ctx, surroundings)
