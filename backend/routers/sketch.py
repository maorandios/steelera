"""Sketch-mode AI analysis endpoints."""

from fastapi import APIRouter

from core.sketch_intent import analyze_sketch_request
from schemas.sketch import SketchAnalyzeRequest, SketchAnalyzeResponse

router = APIRouter(prefix="/api/sketch", tags=["sketch"])


@router.post("/analyze", response_model=SketchAnalyzeResponse)
async def analyze_sketch(request: SketchAnalyzeRequest) -> SketchAnalyzeResponse:
    return analyze_sketch_request(
        elements=request.project_elements,
        start=request.start_node,
        end=request.end_node,
        intent_override=request.intent_override,
        shed_params=request.shed_params,
        site_context=request.site_context,
        z_coords_mm=request.z_coords_mm,
    )
