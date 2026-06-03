from pydantic import BaseModel, Field

from schemas.structural import RenderedStructuralElement


class ProjectState(BaseModel):
    """Universal parametric project state (version 2)."""

    version: int = 2
    elements: list[RenderedStructuralElement] = Field(default_factory=list)
