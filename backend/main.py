from core.env_loader import load_env

load_env()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from catalog_loader import list_profiles
from core.openai_client import build_system_prompt, run_chat_turn
from routers.export import router as export_router
from routers.macro import router as macro_router
from routers.model_edit import router as model_edit_router
from routers.site import router as site_router
from schemas.chat import ChatRequest, ChatResponse, ChatResponseMessage

app = FastAPI(title="Steelera API", version="0.3.0-spatial")
app.include_router(macro_router)
app.include_router(model_edit_router)
app.include_router(export_router)
app.include_router(site_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/catalog")
async def catalog() -> dict:
    return {"profiles": list_profiles()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat pipeline with spatial awareness.

    Reads projectElements from the request body, formats them into a text
    summary, and injects that into the GPT-4o-mini system prompt so the
    model can anchor new members to existing ones.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    state = request.resolved_state()
    spatial_context = build_system_prompt(
        state.projectElements,
        target_element_id=request.target_element_id,
        selection_context=request.selection_context,
    )

    try:
        content, statuses, project_state, ui_block, shed_config = run_chat_turn(
            request.messages,
            state,
            spatial_context=spatial_context,
            target_element_id=request.target_element_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    from core.project_session import set_elements

    set_elements(list(project_state.projectElements))
    elements = [e.model_dump() for e in project_state.projectElements]

    return ChatResponse(
        message=ChatResponseMessage(content=content, ui_block=ui_block),
        statuses=statuses,
        projectElements=elements,
        projectState=project_state,
        structural_grid_layout=shed_config,
        shed_assembly_config=shed_config,
    )
