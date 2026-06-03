"""
Optional helper: expand a simple portal-frame shed into generic element specs.

Used for local testing without OpenAI. The live API path uses
generate_structural_elements from the model directly.
"""

import math

from schemas.structural import ElementPosition, StructuralElementSpec


def shed_params_to_element_specs(
    length: float,
    width: float,
    height: float,
    roof_angle: float,
) -> list[StructuralElementSpec]:
    """Decompose a shed into columns, rafters, and purlins as parametric members."""
    specs: list[StructuralElementSpec] = []
    angle_rad = math.radians(roof_angle)
    ridge_rise = (width / 2) * math.tan(angle_rad)

    bay_spacing = min(6.0, max(length / 3, 3.0)) if length > 0 else 6.0
    frame_x: list[float] = []
    x = 0.0
    while x <= length + 1e-6:
        frame_x.append(x)
        if x >= length - 1e-6:
            break
        x += bay_spacing
    if frame_x[-1] < length - 1e-6:
        frame_x.append(length)
    frame_x = sorted(set(round(v, 4) for v in frame_x))

    col_section = 0.2
    for fx in frame_x:
        for z in (0.0, width):
            specs.append(
                StructuralElementSpec(
                    shape_type="I-beam",
                    height=col_section,
                    width=col_section * 1.2,
                    thickness=0.008,
                    length=height,
                    position=ElementPosition(x=fx, y=z, z=0.0),
                    axis="z",
                )
            )

    rafter_len = math.sqrt((width / 2) ** 2 + ridge_rise**2)
    raf_depth = 0.15
    for fx in frame_x:
        for z_start in (0.0, width / 2):
            specs.append(
                StructuralElementSpec(
                    shape_type="I-beam",
                    height=raf_depth,
                    width=raf_depth * 1.5,
                    thickness=0.006,
                    length=rafter_len,
                    position=ElementPosition(x=fx, y=z_start, z=height),
                    axis="y",
                )
            )

    purlin_spacing = 1.2
    px = 0.0
    while px <= length + 1e-6:
        for z, elev in ((0.0, height), (width, height), (width / 2, height + ridge_rise)):
            specs.append(
                StructuralElementSpec(
                    shape_type="C-channel",
                    height=0.1,
                    width=0.15,
                    thickness=0.005,
                    length=width,
                    position=ElementPosition(x=px, y=z, z=elev),
                    axis="y",
                )
            )
        px += purlin_spacing

    return specs
