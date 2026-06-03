from typing import Literal

from pydantic import BaseModel, Field

ShapeType = Literal["I-beam", "C-channel", "Box", "Pipe"]
AxisType = Literal["x", "y", "z"]


class ElementPosition(BaseModel):
    x: float
    y: float
    z: float


class StructuralElementSpec(BaseModel):
    """Parameters returned by the OpenAI tool for one structural member."""

    shape_type: ShapeType
    height: float = Field(gt=0, description="Section height in meters")
    width: float = Field(gt=0, description="Section width or flange width in meters")
    thickness: float = Field(gt=0, description="Wall/web/flange thickness in meters")
    length: float = Field(gt=0, description="Member length in meters")
    position: ElementPosition
    axis: AxisType = Field(
        default="x",
        description="World axis along which length is measured (x, y, or z)",
    )


class RenderedStructuralElement(BaseModel):
    """Universal mesh-ready element sent to the frontend."""

    id: str
    shape_type: ShapeType
    axis: AxisType = "x"
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: tuple[float, float, float]
    height: float
    width: float
    thickness: float
    length: float
    color: str | None = None
