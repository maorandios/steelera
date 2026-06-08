from typing import Any



from fastapi import APIRouter, HTTPException, Request

from pydantic import ValidationError



from core.geometry_engine import cumulative_positions_from_spans, macro_members_to_project_elements

from core.grid_member_catalog import members_from_shed_config

from core.ifc_topology import build_topology_from_layout, stamp_elements_with_topology

from core.member_resolver import layout_to_macro_members

from core.profile_overrides import apply_profile_overrides_to_layout

from core.project_session import get_state, merge_assembly, set_shed_params

from core.shed_config_bridge import legacy_request_to_config

from schemas.macro import GenerateShedRequest, GenerateShedResponse

from schemas.shed_assembly_config import ShedAssemblyConfig

from core.shed_grid_bridge import grid_definition_from_shed_config
from core.shed_proposal import propose_shed_configuration
from schemas.proposal import ShedProposalRequest, ShedProposalResponse
from schemas.spatial_grid import StructuralGridLayout



router = APIRouter(prefix="/api/macro", tags=["macro"])





def _layout_from_shed_config(config: ShedAssemblyConfig) -> StructuralGridLayout:

    cfg = config.with_default_bays()

    return StructuralGridLayout(

        assembly_id=cfg.assembly_id,

        replace_existing=cfg.replace_existing,

        grid_definition=grid_definition_from_shed_config(cfg),

        structural_members=members_from_shed_config(cfg),

    )





def _run_grid_generate(layout: StructuralGridLayout) -> tuple[

    list[dict[str, Any]],

    list[Any],

    dict[str, float | list[float] | str | bool],

    Any,

]:

    macro_members = layout_to_macro_members(layout)

    topology = build_topology_from_layout(layout)

    project_elements = stamp_elements_with_topology(
        macro_members_to_project_elements(macro_members),
        topology,
    )

    gd = layout.grid_definition

    x_spans = list(gd.x_spans)

    z_spans = list(gd.z_spans)

    params = {

        "x_spans": x_spans,

        "z_spans": z_spans,

        "width": cumulative_positions_from_spans(x_spans)[-1],

        "length": cumulative_positions_from_spans(z_spans)[-1],

        "height": gd.height_mm,

        "roof_pitch_deg": 0.0 if gd.roof_style == "flat" else gd.roof_pitch_deg,

        "roof_style": gd.roof_style,

    }

    return macro_members, project_elements, params, topology





def _parse_generate_shed_body(body: Any) -> StructuralGridLayout:

    if not isinstance(body, dict):

        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    if "grid_definition" in body:
        from core.grid_layout_utils import ensure_layout_members

        layout = StructuralGridLayout.model_validate(body)
        layout = ensure_layout_members(layout)
        return apply_profile_overrides_to_layout(layout)

    if "global_parameters" in body and "grid_layout" in body:

        config = ShedAssemblyConfig.model_validate(body).with_default_bays()

        return _layout_from_shed_config(config)

    legacy = GenerateShedRequest.model_validate(body)

    return _layout_from_shed_config(legacy_request_to_config(legacy))





@router.post("/generate-shed", response_model=GenerateShedResponse)

async def generate_shed(request: Request) -> GenerateShedResponse:

    """Generate shed from universal grid layout (preferred) or legacy config bodies."""

    try:

        body = await request.json()

    except Exception as exc:

        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc



    try:

        layout = _parse_generate_shed_body(body)

        macro_members, project_elements, stored_params, topology = _run_grid_generate(layout)

        all_elements = merge_assembly(

            layout.assembly_id,

            project_elements,

            replace_existing=layout.replace_existing,

        )

    except ValidationError as exc:

        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    except ValueError as exc:

        raise HTTPException(status_code=422, detail=str(exc)) from exc



    set_shed_params(layout.assembly_id, stored_params)



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

        assembly_id=layout.assembly_id,

        elements=macro_members,

        projectElements=all_elements,

        projectState=state,

        counts=counts,

        structural_topology=topology,

    )


@router.post("/propose-shed", response_model=ShedProposalResponse)
async def propose_shed(request: ShedProposalRequest) -> ShedProposalResponse:
    """Deterministic engineering proposal from onboarding wizard inputs."""
    try:
        return propose_shed_configuration(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


