from typing import Literal

from pydantic import BaseModel, Field

from schemas.elements import ProjectElementMm
from schemas.project import ProjectState


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    projectElements: list[ProjectElementMm] = Field(default_factory=list)
    projectState: ProjectState | None = None

    def resolved_state(self) -> ProjectState:
        if self.projectState is not None:
            return self.projectState
        return ProjectState(projectElements=self.projectElements or [])


class ChatResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatResponse(BaseModel):
    message: ChatResponseMessage
    statuses: list[str] = Field(default_factory=list)
    projectElements: list[ProjectElementMm] = Field(default_factory=list)
    projectState: ProjectState | None = None
