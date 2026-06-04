from fastapi import APIRouter, HTTPException

from core.geometry_engine import (
    cumulative_positions_from_spans,
    generate_shed_macro,
    macro_members_to_project_elements,
    parse_bay_spans_mm,
    resolve_x_spans_mm,
    resolve_z_spans_mm,
)
from core.project_session import get_state, merge_assembly, set_shed_params
from schemas.macro import GenerateShedRequest, GenerateShedResponse

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.post("/generate-shed", response_model=GenerateShedResponse)
async def generate_shed(request: GenerateShedRequest) -> GenerateShedResponse:
    """
    Generate a parametric portal-frame shed and merge it into the server session.
    """
    try:
        x_spans = resolve_x_spans_mm(x_spans=request.x_spans, width=request.width)
        z_spans = resolve_z_spans_mm(
            z_spans=request.z_spans,
            length=request.length,
            frame_spacing=request.frame_spacing,
        )
        total_width = cumulative_positions_from_spans(x_spans)[-1]
        total_length = cumulative_positions_from_spans(z_spans)[-1]
        macro_members = generate_shed_macro(
            assembly_id=request.assembly_id,
            x_spans=x_spans,
            z_spans=z_spans,
            height=request.height,
            roof_pitch_deg=request.roof_pitch_deg,
            purlin_spacing=request.purlin_spacing,
        )
        project_elements = macro_members_to_project_elements(macro_members)
        all_elements = merge_assembly(
            request.assembly_id,
            project_elements,
            replace_existing=request.replace_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    set_shed_params(
        request.assembly_id,
        {
            "x_spans": x_spans,
            "z_spans": z_spans,
            "width": total_width,
            "length": total_length,
            "height": request.height,
            "roof_pitch_deg": request.roof_pitch_deg,
            "purlin_spacing": request.purlin_spacing,
        },
    )

    counts = {
        "columns": sum(1 for m in macro_members if m["id"].startswith("shed-col-")),
        "rafters": sum(1 for m in macro_members if m["id"].startswith("shed-raf-")),
        "purlins": sum(1 for m in macro_members if m["id"].startswith("shed-purl-")),
        "total_generated": len(macro_members),
        "total_in_session": len(all_elements),
    }

    state = get_state()
    return GenerateShedResponse(
        assembly_id=request.assembly_id,
        elements=macro_members,
        projectElements=all_elements,
        projectState=state,
        counts=counts,
    )
