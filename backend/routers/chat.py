from fastapi import APIRouter, HTTPException

from core.openai_client import run_chat_turn
from schemas.chat import ChatRequest, ChatResponse, ChatResponseMessage

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    try:
        content, statuses, project_state = run_chat_turn(
            request.messages,
            request.projectState,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return ChatResponse(
        message=ChatResponseMessage(content=content),
        statuses=statuses,
        projectState=project_state,
    )
