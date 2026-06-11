from fastapi import APIRouter, HTTPException

from core.ground_placement import collect_ground_placement_nodes
from core.model_edit import (
    collect_snap_nodes,
    delete_members,
    place_brace_leg,
    place_bracing_cross,
    place_grid_column,
    place_grid_tie_beam,
    update_member_profiles,
)
from schemas.model_edit import (
    DeleteMembersRequest,
    ModelEditBody,
    ModelEditResponse,
    PlaceBraceLegRequest,
    PlaceBracingCrossRequest,
    GroundPlacementNodesRequest,
    PlaceGridColumnRequest,
    PlaceGridTieBeamRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/api/model", tags=["model"])


class UpdateProfileBody(UpdateProfileRequest, ModelEditBody):
    pass


class DeleteMembersBody(DeleteMembersRequest, ModelEditBody):
    pass


class PlaceBraceLegBody(PlaceBraceLegRequest, ModelEditBody):
    pass


class PlaceBracingCrossBody(PlaceBracingCrossRequest, ModelEditBody):
    pass


class PlaceGridColumnBody(PlaceGridColumnRequest, ModelEditBody):
    pass


class PlaceGridTieBeamBody(PlaceGridTieBeamRequest, ModelEditBody):
    pass


class GroundPlacementNodesBody(GroundPlacementNodesRequest, ModelEditBody):
    pass


@router.post("/update-profile", response_model=ModelEditResponse)
async def api_update_profile(body: UpdateProfileBody) -> ModelEditResponse:
    try:
        updated, changed = update_member_profiles(
            body.project_elements,
            profile=body.profile,
            element_ids=body.element_ids or None,
            reference_element_id=body.reference_element_id,
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    scope_label = body.scope.replace("_", " ")
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=changed,
        message=f"Updated profile to {body.profile} on {len(changed)} member(s) ({scope_label}).",
    )


@router.post("/delete-members", response_model=ModelEditResponse)
async def api_delete_members(body: DeleteMembersBody) -> ModelEditResponse:
    try:
        updated, deleted = delete_members(
            body.project_elements,
            element_ids=body.element_ids or None,
            reference_element_id=body.reference_element_id,
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=deleted,
        message=f"Removed {len(deleted)} member(s).",
    )


@router.post("/place-brace-leg", response_model=ModelEditResponse)
async def api_place_brace_leg(body: PlaceBraceLegBody) -> ModelEditResponse:
    try:
        updated, created = place_brace_leg(
            body.project_elements,
            start_mm=(body.start_mm.x, body.start_mm.y, body.start_mm.z),
            end_mm=(body.end_mm.x, body.end_mm.y, body.end_mm.z),
            profile=body.profile,
            assembly_id=body.assembly_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message="Added bracing member between picked nodes.",
    )


@router.post("/place-bracing-cross", response_model=ModelEditResponse)
async def api_place_bracing_cross(body: PlaceBracingCrossBody) -> ModelEditResponse:
    try:
        updated, created = place_bracing_cross(
            body.project_elements,
            start_a=(body.start_a_mm.x, body.start_a_mm.y, body.start_a_mm.z),
            end_a=(body.end_a_mm.x, body.end_a_mm.y, body.end_a_mm.z),
            start_b=(body.start_b_mm.x, body.start_b_mm.y, body.start_b_mm.z),
            end_b=(body.end_b_mm.x, body.end_b_mm.y, body.end_b_mm.z),
            profile=body.profile,
            assembly_id=body.assembly_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=f"Added X-bracing ({len(created)} members).",
    )


@router.post("/place-grid-column", response_model=ModelEditResponse)
async def api_place_grid_column(body: PlaceGridColumnBody) -> ModelEditResponse:
    try:
        updated, created = place_grid_column(
            body.project_elements,
            x_axis=body.x_axis,
            z_axis=body.z_axis,
            profile=body.profile,
            grid=body.grid,
            trussed_z_labels=body.trussed_z_labels,
            assembly_id=body.assembly_id,
            offset_mm=body.offset_mm,
            connect_to=body.connect_to,
            truss_type=body.truss_type,
            add_tie_in_bay=body.add_tie_in_bay,
            tie_profile=body.tie_profile,
            bay_z_start=body.bay_z_start,
            bay_z_end=body.bay_z_end,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=f"Placed column {body.profile} at {body.x_axis} · {body.z_axis}.",
    )


@router.post("/place-grid-tie-beam", response_model=ModelEditResponse)
async def api_place_grid_tie_beam(body: PlaceGridTieBeamBody) -> ModelEditResponse:
    try:
        updated, created = place_grid_tie_beam(
            body.project_elements,
            x_axis=body.x_axis,
            z_start=body.z_start,
            z_end=body.z_end,
            profile=body.profile,
            elevation=body.elevation,
            grid=body.grid,
            assembly_id=body.assembly_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=(
            f"Placed tie beam {body.profile} at {body.x_axis} "
            f"({body.z_start} → {body.z_end}, {body.elevation})."
        ),
    )


@router.post("/ground-placement-nodes")
async def api_ground_placement_nodes(body: GroundPlacementNodesBody) -> dict:
    nodes = collect_ground_placement_nodes(
        body.grid,
        trussed_z_labels=body.trussed_z_labels,
        truss_type=body.truss_type,
        bay_z_start=body.bay_z_start,
        bay_z_end=body.bay_z_end,
        extra_wall_offsets_mm=body.extra_wall_offsets_mm or None,
    )
    return {
        "nodes": [
            {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "z": n.z,
                "x_axis": n.x_axis,
                "z_axis": n.z_axis,
                "offset_mm": n.offset_mm,
                "label": n.label,
                "kind": n.kind,
                "connect_to": n.connect_to,
            }
            for n in nodes
        ]
    }


@router.post("/snap-nodes")
async def api_snap_nodes(body: ModelEditBody) -> dict:
    nodes = collect_snap_nodes(body.project_elements)
    return {
        "nodes": [
            {"id": nid, "x": pt[0], "y": pt[1], "z": pt[2]}
            for nid, pt in nodes
        ]
    }
