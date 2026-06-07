"""
Universal structural grid engine — named 3D node matrix and sub-node resolution.

Python computes grid intersections and elevations only; members snap via logical references.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal

from core.geometry_engine import cumulative_positions_from_spans
from core.roof_geometry import RoofGeometry, compute_roof_geometry, roof_elevation_at_x
from schemas.spatial_grid import GridDefinition, GridNodeReference

_AXIS_SUBDIV = re.compile(
    r"^([A-Z]+)(?:[-+](\d+)/(\d+))?$",
    re.IGNORECASE,
)
_Z_SUBDIV = re.compile(
    r"^(\d+)(?:[-+](\d+)/(\d+))?$",
)

ElevationKind = Literal["x", "z"]


def _x_axis_label(index: int) -> str:
    if index < 26:
        return chr(65 + index)
    first = index // 26 - 1
    second = index % 26
    return chr(65 + first) + chr(65 + second)


def _resolve_subdivided_coord(
    ref: str,
    labels: list[str],
    coords: dict[str, float],
    *,
    subdiv_re: re.Pattern[str],
    axis_kind: str,
) -> float:
    """
    Resolve axis label with optional fraction (A+2/5 or 5+1/2).

    Forward span: base → next line when next exists.
    Last line + fraction: previous → base (5+1/2 = halfway between 4 and 5).
    """
    from core.grid_normalize import normalize_axis_ref

    is_x = axis_kind == "x"
    text = normalize_axis_ref(ref, is_x=is_x)
    m = subdiv_re.match(text.upper() if is_x else text)
    if not m:
        key = text.upper() if is_x else text
        if key in coords:
            return coords[key]
        raise ValueError(
            f"Invalid {axis_kind} axis reference: {ref!r}; known: {labels}"
        )

    base_label = m.group(1) if is_x else str(int(m.group(1)))
    lookup = base_label if base_label in coords else text
    if lookup not in coords:
        raise ValueError(f"Unknown {axis_kind} axis {base_label!r}; known: {labels}")

    if not m.group(2):
        return coords[lookup]

    num = int(m.group(2))
    den = int(m.group(3))
    if den <= 0 or num < 0:
        raise ValueError(f"Invalid subdivision {ref!r}")

    frac = min(num / den, 1.0)
    idx = labels.index(lookup if lookup in labels else base_label)

    if idx < len(labels) - 1:
        a = coords[labels[idx]]
        b = coords[labels[idx + 1]]
    elif idx > 0:
        a = coords[labels[idx - 1]]
        b = coords[labels[idx]]
    else:
        return coords[labels[0]]

    return round(a + (b - a) * frac, 3)


def _parse_axis_ref(
    ref: str,
    *,
    labels: list[str],
    coords: dict[str, float],
) -> float:
    return _resolve_subdivided_coord(
        ref, labels, coords, subdiv_re=_AXIS_SUBDIV, axis_kind="x"
    )


def _parse_z_ref(ref: str, labels: list[str], coords: dict[str, float]) -> float:
    return _resolve_subdivided_coord(
        ref, labels, coords, subdiv_re=_Z_SUBDIV, axis_kind="z"
    )


def _parse_x_ref(ref: str, labels: list[str], coords: dict[str, float]) -> float:
    from core.grid_normalize import normalize_axis_ref

    text = normalize_axis_ref(ref, is_x=True)
    if text in coords and "+" not in text and "-" not in text:
        return coords[text]
    return _parse_axis_ref(text, labels=labels, coords=coords)


_ELEV_SUBDIV = re.compile(
    r"^([a-z_]+)(?:\+(\d+)/(\d+))?$",
    re.IGNORECASE,
)


@dataclass
class StructuralGridEngine:
    """
    3D matrix of named grid nodes from spans and critical elevations.
    """

    definition: GridDefinition
    roof: RoofGeometry
    total_width_mm: float
    total_length_mm: float
    x_labels: list[str] = field(default_factory=list)
    z_labels: list[str] = field(default_factory=list)
    x_coords_mm: dict[str, float] = field(default_factory=dict)
    z_coords_mm: dict[str, float] = field(default_factory=dict)
    nodes: dict[str, tuple[float, float, float]] = field(default_factory=dict)

    @classmethod
    def from_definition(cls, definition: GridDefinition) -> StructuralGridEngine:
        x_spans = list(definition.x_spans)
        z_spans = list(definition.z_spans)
        x_positions = cumulative_positions_from_spans(x_spans)
        z_positions = cumulative_positions_from_spans(z_spans)
        total_width = x_positions[-1]
        total_length = z_positions[-1]

        style, pitch = definition.roof_style, definition.roof_pitch_deg
        if style == "flat":
            pitch = 0.0
        roof = compute_roof_geometry(
            style,
            pitch,
            total_width,
            definition.height_mm,
            mono_high_side=getattr(definition, "mono_high_side", "B"),
        )

        x_labels = [_x_axis_label(i) for i in range(len(x_positions))]
        z_labels = [str(i + 1) for i in range(len(z_positions))]
        x_coords = {label: x_positions[i] for i, label in enumerate(x_labels)}
        z_coords = {label: z_positions[i] for i, label in enumerate(z_labels)}

        engine = cls(
            definition=definition,
            roof=roof,
            total_width_mm=total_width,
            total_length_mm=total_length,
            x_labels=x_labels,
            z_labels=z_labels,
            x_coords_mm=x_coords,
            z_coords_mm=z_coords,
        )
        engine._register_primary_nodes()
        return engine

    def _register_primary_nodes(self) -> None:
        """Cache primary intersections at ground, eave, roof, apex."""
        for x_label in self.x_labels:
            for z_label in self.z_labels:
                for elev in ("ground", "eave", "roof", "apex"):
                    key = self._node_key(x_label, z_label, elev)
                    self.nodes[key] = self.resolve_node(
                        GridNodeReference(x_axis=x_label, z_axis=z_label, elevation=elev)
                    )

    @staticmethod
    def _node_key(x_axis: str, z_axis: str, elevation: str) -> str:
        return f"{x_axis}|{z_axis}|{elevation}"

    def subdivide_x(self, axis_a: str, axis_b: str, divisions: int) -> list[str]:
        """Equal X references between two resolvable X addresses (excludes endpoints)."""
        if divisions < 1:
            raise ValueError("divisions must be >= 1")
        a = axis_a.strip().upper()
        _ = self.resolve_x_mm(axis_a)
        _ = self.resolve_x_mm(axis_b)
        return [f"{a}+{i}/{divisions}" for i in range(1, divisions)]

    def subdivide_z(self, axis_a: str, axis_b: str, divisions: int) -> list[str]:
        if divisions < 1:
            raise ValueError("divisions must be >= 1")
        a = axis_a.strip()
        _ = self.resolve_z_mm(axis_a)
        _ = self.resolve_z_mm(axis_b)
        return [f"{a}+{i}/{divisions}" for i in range(1, divisions)]

    def subdivide_elevation(
        self,
        elevation_a: str,
        elevation_b: str,
        divisions: int,
        *,
        x_mm: float,
    ) -> list[str]:
        """Named elevation fractions at a fixed plan position (for girts, etc.)."""
        if divisions < 1:
            raise ValueError("divisions must be >= 1")
        ya = self._elevation_mm(elevation_a, x_mm)
        yb = self._elevation_mm(elevation_b, x_mm)
        return [
            f"{elevation_a}+{i}/{divisions}"
            for i in range(1, divisions)
        ]

    def _elevation_mm(self, elevation: str, x_mm: float) -> float:
        from core.grid_normalize import normalize_elevation

        # AI-defined custom levels (e.g. mezzanine floor) take precedence and are
        # element-agnostic: a flat absolute height usable by any structure type.
        custom = self.definition.custom_levels or {}
        raw_key = str(elevation).strip()
        if raw_key in custom:
            return float(custom[raw_key])
        if raw_key.lower() in custom:
            return float(custom[raw_key.lower()])

        text = normalize_elevation(elevation)
        if text in custom:
            return float(custom[text])
        m = _ELEV_SUBDIV.match(text)
        if not m:
            raise ValueError(f"Unknown elevation {elevation!r}")

        if m.group(1) in custom and not m.group(2):
            return float(custom[m.group(1)])

        base = m.group(1)
        if base in ("ground",):
            y0 = 0.0
            if m.group(2):
                num = int(m.group(2))
                den = int(m.group(3))
                y1 = self.roof.eave_y
                return round(y0 + (y1 - y0) * (num / den), 3)
        elif base in ("eave",):
            y0 = self.roof.eave_y
        elif base in ("roof", "ridge"):
            y0 = roof_elevation_at_x(x_mm, self.roof, self.total_width_mm)
        elif base in ("apex",):
            y0 = (
                self.roof.ridge_y
                if abs(x_mm - self.roof.ridge_x) < 1.0
                else roof_elevation_at_x(x_mm, self.roof, self.total_width_mm)
            )
        else:
            raise ValueError(
                f"Unknown elevation {base!r}; use ground, eave, roof, apex, ridge"
            )

        if not m.group(2):
            return y0

        num = int(m.group(2))
        den = int(m.group(3))
        if den <= 0:
            raise ValueError(f"Invalid elevation fraction in {elevation!r}")

        if base == "eave":
            y1 = roof_elevation_at_x(x_mm, self.roof, self.total_width_mm)
            return y0 + (y1 - y0) * (num / den)

        raise ValueError(f"Elevation subdivision not supported for {elevation!r}")

    def resolve_x_mm(self, x_axis: str) -> float:
        return _parse_x_ref(x_axis, self.x_labels, self.x_coords_mm)

    def resolve_z_mm(self, z_axis: str) -> float:
        return _parse_z_ref(z_axis, self.z_labels, self.z_coords_mm)

    def resolve_node(self, ref: GridNodeReference) -> tuple[float, float, float]:
        x_mm = self.resolve_x_mm(ref.x_axis)
        z_mm = self.resolve_z_mm(ref.z_axis)
        off = ref.offset_mm or {}
        x_eff = x_mm + float(off.get("x", 0))
        z_eff = z_mm + float(off.get("z", 0))
        from core.grid_normalize import normalize_elevation

        elev_text = normalize_elevation(ref.elevation)

        if "+" in elev_text and not _ELEV_SUBDIV.match(elev_text):
            parts = elev_text.split("+", 1)
            base = parts[0]
            frac = parts[1]
            m = re.match(r"^(\d+)/(\d+)$", frac)
            if m:
                y0 = self._elevation_mm(base, x_eff)
                y1 = self._elevation_mm(
                    "roof" if base == "eave" else "apex",
                    x_eff,
                )
                return (
                    round(x_eff, 3),
                    round(y0 + (y1 - y0) * int(m.group(1)) / int(m.group(2)), 3),
                    round(z_eff, 3),
                )

        y_mm = self._elevation_mm(elev_text, x_eff)
        return (
            round(x_eff, 3),
            round(y_mm + float(off.get("y", 0)), 3),
            round(z_eff, 3),
        )

    def grid_summary(self) -> dict:
        return {
            "x_axes": self.x_labels,
            "z_axes": self.z_labels,
            "x_coords_mm": self.x_coords_mm,
            "z_coords_mm": self.z_coords_mm,
            "elevations": ["ground", "eave", "roof", "apex", "ridge"],
            "total_width_mm": self.total_width_mm,
            "total_length_mm": self.total_length_mm,
            "ridge_x_mm": self.roof.ridge_x,
            "eave_y_mm": self.roof.eave_y,
            "apex_y_mm": self.roof.ridge_y,
        }
