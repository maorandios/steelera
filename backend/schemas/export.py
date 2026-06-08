"""IFC export request bodies."""

from typing import Any, Literal

from pydantic import BaseModel, Field

IfcSchemaLiteral = Literal["IFC2X3", "IFC4"]


class ExportIfcRequest(BaseModel):
    structural_topology: dict[str, Any] = Field(
        ...,
        description="Steelera IFCTopology.model_dump() payload.",
    )
    schema_version: IfcSchemaLiteral = "IFC4"
    filename: str | None = Field(
        None,
        description="Optional download filename (without path).",
    )
