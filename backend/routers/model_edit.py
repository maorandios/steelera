from fastapi import APIRouter, HTTPException

from core.model_edit import (
    collect_snap_nodes,
    delete_members,
    place_brace_leg,
    place_bracing_cross,
    update_member_profiles,
)
from schemas.model_edit import (
    DeleteMembersRequest,
    ModelEditBody,
    ModelEditResponse,
    PlaceBraceLegRequest,
    PlaceBracingCrossRequest,
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


@router.post("/snap-nodes")
async def api_snap_nodes(body: ModelEditBody) -> dict:
    nodes = collect_snap_nodes(body.project_elements)
    return {
        "nodes": [
            {"id": nid, "x": pt[0], "y": pt[1], "z": pt[2]}
            for nid, pt in nodes
        ]
    }
