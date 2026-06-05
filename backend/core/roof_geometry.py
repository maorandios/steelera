"""Roof elevation model — used only to populate grid elevation levels (not per-member math)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class RoofGeometry:
    style: str
    pitch_rad: float
    ridge_x: float
    ridge_y: float
    eave_y: float
    left_span: float
    right_span: float
    mono_high_side: str = "B"  # which X end is high for a mono pitch ("A"=x0, "B"=xmax)

    @property
    def is_flat(self) -> bool:
        return self.style == "flat"

    @property
    def is_mono(self) -> bool:
        return self.style == "mono_pitch"


def normalize_roof_style_and_pitch(
    roof_style: str,
    roof_pitch_deg: float,
) -> tuple[str, float]:
    style = roof_style.strip().lower()
    pitch = max(0.0, float(roof_pitch_deg))
    if style == "flat" or pitch < 1e-6:
        return "flat", 0.0
    return style, pitch


def compute_roof_geometry(
    roof_style: str,
    roof_pitch_deg: float,
    total_width: float,
    eave_height: float,
    mono_high_side: str = "B",
) -> RoofGeometry:
    style, pitch_deg = normalize_roof_style_and_pitch(roof_style, roof_pitch_deg)
    pitch_rad = math.radians(pitch_deg)
    eave = float(eave_height)
    width = max(float(total_width), 0.0)
    high_side = "A" if str(mono_high_side).strip().upper() == "A" else "B"

    if style == "flat":
        half = width / 2.0
        return RoofGeometry(
            style=style,
            pitch_rad=0.0,
            ridge_x=half,
            ridge_y=eave,
            eave_y=eave,
            left_span=half,
            right_span=half,
        )

    if style == "mono_pitch":
        rise = width * math.tan(pitch_rad)
        # ridge_x marks the HIGH end: x=0 for side A, x=width for side B.
        ridge_x = 0.0 if high_side == "A" else width
        return RoofGeometry(
            style=style,
            pitch_rad=pitch_rad,
            ridge_x=ridge_x,
            ridge_y=eave + rise,
            eave_y=eave,
            left_span=width,
            right_span=0.0,
            mono_high_side=high_side,
        )

    ridge_x = width / 2.0
    left_rise = ridge_x * math.tan(pitch_rad)
    return RoofGeometry(
        style=style,
        pitch_rad=pitch_rad,
        ridge_x=ridge_x,
        ridge_y=eave + left_rise,
        eave_y=eave,
        left_span=ridge_x,
        right_span=width - ridge_x,
    )


def roof_elevation_at_x(x_mm: float, roof: RoofGeometry, total_width: float) -> float:
    if roof.is_flat:
        return roof.eave_y
    if roof.is_mono:
        # Rise measured from the LOW end toward the high end.
        if roof.mono_high_side == "A":
            return roof.eave_y + (total_width - x_mm) * math.tan(roof.pitch_rad)
        return roof.eave_y + x_mm * math.tan(roof.pitch_rad)
    if x_mm <= roof.ridge_x + 1e-6:
        return roof.eave_y + x_mm * math.tan(roof.pitch_rad)
    return roof.eave_y + (total_width - x_mm) * math.tan(roof.pitch_rad)
