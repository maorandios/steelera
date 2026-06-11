"""Unified structural advisory endpoints."""

from fastapi import APIRouter

from core.structural_advise import advise_structural
from schemas.structural_advise import StructuralAdviseRequest, StructuralAdviseResponse

router = APIRouter(prefix="/api/structural", tags=["structural"])


@router.post("/advise", response_model=StructuralAdviseResponse)
async def structural_advise(request: StructuralAdviseRequest) -> StructuralAdviseResponse:
    return advise_structural(request)
