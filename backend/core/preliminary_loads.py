"""Preliminary member force estimates for portal-frame / Pratt-truss sheds."""

from __future__ import annotations

import math
from dataclasses import dataclass

from schemas.site import SiteContext

# Roof dead load screening (kN/m²): cladding + purlins + steel self-weight allowance.
ROOF_DEAD_KN_M2 = 0.35
# Wind pressure scale: q_w ≈ WIND_K * load_index^1.15 (kN/m²).
WIND_PRESSURE_K = 0.055
# Portal frame moment multiplier vs simply-supported beam.
PORTAL_MOMENT_FACTOR = 1.35
# Column base fixity / haunch stiffening (reduces moment demand screening).
COLUMN_MOMENT_FACTOR = 0.85


@dataclass(frozen=True)
class PreliminaryLoads:
    effective_load_index: float
    roof_pressure_kn_m2: float
    frame_line_load_kn_m: float
    column_axial_kn: float
    column_moment_knm: float
    rafter_moment_knm: float
    chord_axial_kn: float
    truss_depth_mm: float
    web_axial_kn: float
    web_length_mm: float
    tie_beam_axial_kn: float
    tie_beam_length_mm: float
    bracing_axial_kn: float
    bracing_length_mm: float


def roof_design_pressure_kn_m2(effective_load_index: float) -> float:
    """Combined ULS roof pressure from dead + wind proxy index."""
    wind = WIND_PRESSURE_K * effective_load_index**1.15
    return ROOF_DEAD_KN_M2 + wind


def truss_depth_mm(
    *,
    width_mm: float,
    height_mm: float,
    roof_pitch_deg: float,
) -> float:
    """Pratt truss depth at mid-span (mm) for chord force estimate."""
    pitch_rad = math.radians(max(0.0, roof_pitch_deg))
    half_span = width_mm / 2.0
    ridge_rise = half_span * math.tan(pitch_rad)
    # Eave contributes to knee depth but is capped — chord force must not drop
    # artificially on very tall buildings.
    eave_contrib = min(0.20 * height_mm, width_mm * 0.12)
    return max(800.0, ridge_rise + eave_contrib)


def estimate_web_forces(
    *,
    chord_axial_kn: float,
    truss_depth_mm: float,
    panel_length_mm: float,
) -> tuple[float, float]:
    """Pratt diagonal web axial force and geometric length (screening)."""
    panel_m = max(panel_length_mm / 1000.0, 0.8)
    depth_m = max(truss_depth_mm / 1000.0, 0.8)
    sin_angle = max(depth_m / math.hypot(panel_m, depth_m), 0.35)
    web_n = chord_axial_kn / sin_angle
    web_len = math.hypot(panel_m, depth_m) * 1000.0
    return round(web_n, 2), round(web_len, 1)


def estimate_tie_beam_force(
    *,
    width_mm: float,
    length_mm: float,
    height_mm: float,
    bay_spacing_mm: float,
    effective_load_index: float,
    site: SiteContext,
) -> tuple[float, float]:
    """Longitudinal eave/ridge tie axial demand (screening)."""
    span_m = width_mm / 1000.0
    height_m = height_mm / 1000.0
    length_m = length_mm / 1000.0
    bay_m = bay_spacing_mm / 1000.0
    exposure_factor = 1.15 if site.exposure == "open" else 1.0
    wind_q = WIND_PRESSURE_K * effective_load_index**1.15

    # Wind thrust on end frame transferred into longitudinal ties.
    tie_n = wind_q * exposure_factor * height_m * bay_m * 1.25
    if length_m >= 40.0:
        tie_n *= 1.0 + min((length_m - 40.0) / 60.0, 0.35)
    if height_m >= 10.0:
        tie_n *= 1.0 + min((height_m - 10.0) / 15.0, 0.30)
    if span_m >= 20.0:
        tie_n *= 1.0 + min((span_m - 20.0) / 20.0, 0.25)

    return round(tie_n, 2), float(length_mm)


def estimate_bracing_force(
    *,
    height_mm: float,
    bay_spacing_mm: float,
    effective_load_index: float,
    site: SiteContext,
) -> tuple[float, float]:
    """Wall/roof X-brace diagonal axial demand and length (screening)."""
    height_m = height_mm / 1000.0
    bay_m = bay_spacing_mm / 1000.0
    exposure_factor = 1.15 if site.exposure == "open" else 1.0
    wind_q = WIND_PRESSURE_K * effective_load_index**1.15

    # Braced panel: wind thrust into active tension diagonal (X-brace screening).
    panel_n = wind_q * exposure_factor * height_m * bay_m * 0.45
    if height_m >= 12.0:
        panel_n *= 1.0 + min((height_m - 12.0) / 15.0, 0.25)
    if height_m >= 18.0:
        panel_n *= 1.08

    half_bay = max(bay_spacing_mm / 2.0, 1500.0)
    brace_len = math.hypot(height_mm, half_bay)
    return round(panel_n, 2), round(brace_len, 1)


def estimate_preliminary_loads(
    *,
    width_mm: float,
    length_mm: float,
    height_mm: float,
    roof_pitch_deg: float,
    bay_spacing_mm: float,
    effective_load_index: float,
    site: SiteContext,
    roof_style: str = "duo_pitch",
) -> PreliminaryLoads:
    """Screening-level frame forces from geometry and site load index."""
    span_m = width_mm / 1000.0
    height_m = height_mm / 1000.0
    bay_m = bay_spacing_mm / 1000.0
    length_m = max(length_mm / 1000.0, bay_m)

    q = roof_design_pressure_kn_m2(effective_load_index)
    # Each frame carries tributary roof strip ≈ bay spacing.
    w = q * bay_m
    exposure_factor = 1.15 if site.exposure == "open" else 1.0
    wind_q = max(0.0, q - ROOF_DEAD_KN_M2)

    # Portal rafter / truss top-chord screening moment.
    rafter_m = PORTAL_MOMENT_FACTOR * w * span_m**2 / 8.0

    depth_mm = truss_depth_mm(
        width_mm=width_mm,
        height_mm=height_mm,
        roof_pitch_deg=roof_pitch_deg,
    )
    depth_m = max(depth_mm / 1000.0, span_m * 0.12)
    chord_gravity = w * span_m**2 / (8.0 * depth_m)
    # Wind on tall open frames adds axial chord demand (screening).
    chord_wind = (
        wind_q
        * exposure_factor
        * span_m
        * height_m
        / max(4.0 * depth_m, 1.0)
        * 0.40
    )
    chord_n = chord_gravity + chord_wind

    # Column axial: half the frame vertical reaction with dynamic allowance.
    column_n = 1.10 * w * span_m / 2.0

    # Column major-axis moment from wind on end wall + frame sway (screening).
    end_wall_pressure = wind_q * exposure_factor * 1.25
    num_frames = max(2, round(length_m / bay_m) + 1)
    wind_per_column = end_wall_pressure * height_m * (length_m / num_frames)
    column_m = COLUMN_MOMENT_FACTOR * wind_per_column * height_m / 2.0

    if roof_style == "mono_pitch":
        # Asymmetric mono roof: higher uplift/drift on tall side (screening).
        pitch_rad = math.radians(max(0.0, roof_pitch_deg))
        mono_factor = 1.0 + min(math.tan(pitch_rad) * 0.35, 0.25)
        chord_wind *= 1.0 + min(mono_factor - 1.0 + 0.12, 0.30)
        chord_n = chord_gravity + chord_wind
        column_m *= 1.0 + min(mono_factor - 1.0 + 0.10, 0.28)
        column_n *= 1.0 + min(mono_factor - 1.0 + 0.05, 0.15)

    panel_mm = max(0.85 * bay_spacing_mm, 1200.0)
    web_n, web_len = estimate_web_forces(
        chord_axial_kn=chord_n,
        truss_depth_mm=depth_mm,
        panel_length_mm=panel_mm,
    )
    tie_n, tie_len = estimate_tie_beam_force(
        width_mm=width_mm,
        length_mm=length_mm,
        height_mm=height_mm,
        bay_spacing_mm=bay_spacing_mm,
        effective_load_index=effective_load_index,
        site=site,
    )
    brace_n, brace_len = estimate_bracing_force(
        height_mm=height_mm,
        bay_spacing_mm=bay_spacing_mm,
        effective_load_index=effective_load_index,
        site=site,
    )

    return PreliminaryLoads(
        effective_load_index=effective_load_index,
        roof_pressure_kn_m2=round(q, 3),
        frame_line_load_kn_m=round(w, 3),
        column_axial_kn=round(column_n, 2),
        column_moment_knm=round(column_m, 2),
        rafter_moment_knm=round(rafter_m, 2),
        chord_axial_kn=round(chord_n, 2),
        truss_depth_mm=round(depth_mm, 1),
        web_axial_kn=web_n,
        web_length_mm=web_len,
        tie_beam_axial_kn=tie_n,
        tie_beam_length_mm=tie_len,
        bracing_axial_kn=brace_n,
        bracing_length_mm=brace_len,
    )
