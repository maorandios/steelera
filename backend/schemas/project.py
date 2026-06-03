from pydantic import BaseModel, Field

from schemas.elements import ProjectElementMm


class ProjectState(BaseModel):
    """Milestone 1 project payload (millimeter elements)."""

    version: int = 3
    projectElements: list[ProjectElementMm] = Field(default_factory=list)
