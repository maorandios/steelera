from fastapi import APIRouter, HTTPException

from core.openai_client import run_chat_turn
from schemas.chat import ChatRequest, ChatResponse, ChatResponseMessage

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    try:
        content, statuses, project_state, ui_block, shed_config = run_chat_turn(
            request.messages,
            request.resolved_state(),
            target_element_id=request.target_element_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    from core.project_session import set_elements

    set_elements(list(project_state.projectElements))

    return ChatResponse(
        message=ChatResponseMessage(content=content, ui_block=ui_block),
        statuses=statuses,
        projectElements=[e.model_dump() for e in project_state.projectElements],
        projectState=project_state,
        structural_grid_layout=shed_config,
        shed_assembly_config=shed_config,
    )
