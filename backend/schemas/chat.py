from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.elements import ProjectElementMm
from schemas.project import ProjectState

RoofStyleLiteral = Literal["duo_pitch", "mono_pitch", "flat"]
UiBlockType = Literal["show_component_checklist"]


class ShedChecklistPayload(BaseModel):
    """Baseline shed dimensions extracted from user intent (mm)."""

    width_mm: float | None = None
    length_mm: float | None = None
    height_mm: float | None = None
    roof_style: RoofStyleLiteral | None = None
    roof_pitch_deg: float | None = None
    x_spans: str | None = None
    z_spans: str | None = None

    @field_validator("roof_style", mode="before")
    @classmethod
    def normalize_roof_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if key in ("duo_pitch", "mono_pitch", "flat"):
            return key
        return None


class ChatUiBlock(BaseModel):
    type: UiBlockType
    payload: ShedChecklistPayload


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ui_block: ChatUiBlock | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    projectElements: list[ProjectElementMm] = Field(default_factory=list)
    projectState: ProjectState | None = None
    target_element_id: str | None = None

    def resolved_state(self) -> ProjectState:
        if self.projectState is not None:
            return self.projectState
        return ProjectState(projectElements=self.projectElements or [])


class ChatResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    ui_block: ChatUiBlock | None = None


class ChatResponse(BaseModel):
    message: ChatResponseMessage
    statuses: list[str] = Field(default_factory=list)
    projectElements: list[ProjectElementMm] = Field(default_factory=list)
    projectState: ProjectState | None = None
    structural_grid_layout: dict | None = Field(
        None,
        description="Grid + structural_members from submit_structural_grid_layout; frontend runs macro.",
    )
    shed_assembly_config: dict | None = Field(
        None,
        description="Deprecated alias; use structural_grid_layout.",
    )
