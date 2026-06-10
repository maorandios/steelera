"""Section property estimates from catalog geometry (preliminary EC3 screening)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from catalog_loader import get_profile

E_MPA = 210_000.0
FY_MPA = 355.0


@dataclass(frozen=True)
class SectionProperties:
    profile: str
    shape: str
    area_mm2: float
    iy_mm4: float
    iz_mm4: float
    wpl_y_mm3: float
    wpl_z_mm3: float
    ry_mm: float
    rz_mm: float
    mass_kg_m: float


def _open_i_properties(h: float, b: float, tw: float, tf: float) -> tuple[float, float, float, float, float]:
    """Doubly symmetric I-section: area, Iy, Iz, Wpl_y, Wpl_z (fillet ignored)."""
    hw = h - 2.0 * tf
    area = 2.0 * b * tf + hw * tw
    # Strong axis (y-y): Iy = 2 * (b*tf*(h/2 - tf/2)^2 + b*tf^3/12) + tw*hw^3/12
    d_flange = (h - tf) / 2.0
    iy = 2.0 * (b * tf * d_flange**2 + b * tf**3 / 12.0) + tw * hw**3 / 12.0
    iz = 2.0 * tf * b**3 / 12.0 + hw * tw**3 / 12.0
    wpl_y = b * tf * (h - tf) + tw * hw**2 / 4.0
    wpl_z = b**2 * tf / 2.0 + hw * tw**2 / 4.0
    return area, iy, iz, wpl_y, wpl_z


def _hollow_properties(h: float, b: float, t: float) -> tuple[float, float, float, float, float]:
    """Rectangular / square hollow section."""
    hi = h - 2.0 * t
    bi = b - 2.0 * t
    area = h * b - hi * bi
    iy = (b * h**3 - bi * hi**3) / 12.0
    iz = (h * b**3 - hi * bi**3) / 12.0
    wpl_y = (b * h**2 - bi * hi**2) / 4.0
    wpl_z = (h * b**2 - hi * bi**2) / 4.0
    return area, iy, iz, wpl_y, wpl_z


def _chs_properties(d: float, t: float) -> tuple[float, float, float, float, float]:
    """Circular hollow section."""
    di = d - 2.0 * t
    area = math.pi * (d**2 - di**2) / 4.0
    i = math.pi * (d**4 - di**4) / 64.0
    wpl = (d**3 - di**3) / 6.0
    return area, i, i, wpl, wpl


def _angle_properties(h: float, b: float, t: float) -> tuple[float, float, float, float, float]:
    """Equal-leg angle — screening properties (fillet ignored)."""
    area = t * (h + b - t)
    # Approximate radii of gyration for equal-leg L (typical tables ~0.29a).
    leg = min(h, b)
    rz = 0.29 * leg
    ry = 0.29 * leg
    iz = area * rz**2
    iy = area * ry**2
    wpl_y = area * leg / 2.0
    wpl_z = area * leg / 2.0
    return area, iy, iz, wpl_y, wpl_z


def section_properties(profile_name: str) -> SectionProperties:
    """Return screening section properties for a catalog designation."""
    raw = get_profile(profile_name)
    shape = str(raw.get("shape", "I-beam"))
    h = float(raw["h"])
    b = float(raw["b"])
    tw = float(raw["tw"])
    tf = float(raw["tf"])
    mass = float(raw.get("mass_per_m", 0.0))

    if shape == "CHS":
        d = float(raw.get("d", h))
        t = float(raw.get("t", tw))
        area, iy, iz, wpl_y, wpl_z = _chs_properties(d, t)
    elif shape == "Angle":
        t = float(raw.get("t", tw))
        area, iy, iz, wpl_y, wpl_z = _angle_properties(h, b, t)
    elif shape in ("RHS", "Box") or str(raw.get("family", "")).upper() == "SHS":
        t = float(raw.get("t", tw))
        area, iy, iz, wpl_y, wpl_z = _hollow_properties(h, b, t)
    else:
        area, iy, iz, wpl_y, wpl_z = _open_i_properties(h, b, tw, tf)

    ry = math.sqrt(iy / area) if area > 0 else 0.0
    rz = math.sqrt(iz / area) if area > 0 else 0.0
    return SectionProperties(
        profile=profile_name,
        shape=shape,
        area_mm2=area,
        iy_mm4=iy,
        iz_mm4=iz,
        wpl_y_mm3=wpl_y,
        wpl_z_mm3=wpl_z,
        ry_mm=ry,
        rz_mm=rz,
        mass_kg_m=mass,
    )
