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
        pitch_deg = 0.0 if request.roof_style == "flat" else request.roof_pitch_deg
        macro_members = generate_shed_macro(
            assembly_id=request.assembly_id,
            x_spans=x_spans,
            z_spans=z_spans,
            height=request.height,
            roof_pitch_deg=pitch_deg,
            roof_style=request.roof_style,
            purlin_spacing=request.purlin_spacing,
            girt_spacing_mm=request.girt_spacing_mm,
            use_truss=request.use_truss,
            use_bracing=request.use_bracing,
            use_sag_rods=request.use_sag_rods,
            generate_wall_girts=request.generate_wall_girts,
            generate_tie_beams=request.generate_tie_beams,
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
            "roof_pitch_deg": pitch_deg,
            "roof_style": request.roof_style,
            "purlin_spacing": request.purlin_spacing,
            "girt_spacing_mm": request.girt_spacing_mm,
            "use_truss": request.use_truss,
            "use_bracing": request.use_bracing,
            "use_sag_rods": request.use_sag_rods,
            "generate_wall_girts": request.generate_wall_girts,
            "generate_tie_beams": request.generate_tie_beams,
        },
    )

    def _count_type(element_type: str) -> int:
        return sum(1 for m in macro_members if m.get("element_type") == element_type)

    counts = {
        "columns": _count_type("column"),
        "rafters": _count_type("rafter"),
        "purlins": _count_type("purlin"),
        "wall_girts": _count_type("wall_girt"),
        "tie_beams": _count_type("tie_beam"),
        "bracing": _count_type("bracing"),
        "truss_chords": _count_type("truss_chord"),
        "truss_webs": _count_type("truss_web"),
        "sag_rods": _count_type("sag_rod"),
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
