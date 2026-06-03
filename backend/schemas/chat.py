from typing import Literal

from pydantic import BaseModel, Field

from schemas.project import ProjectState


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    projectState: ProjectState = Field(default_factory=ProjectState)


class ChatResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatResponse(BaseModel):
    message: ChatResponseMessage
    statuses: list[str] = Field(default_factory=list)
    projectState: ProjectState
