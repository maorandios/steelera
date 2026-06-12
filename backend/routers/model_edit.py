from fastapi import APIRouter, HTTPException

from core.ground_placement import collect_ground_placement_nodes
from core.model_edit import (
    collect_snap_nodes,
    delete_members,
    place_brace_leg,
    place_bracing_cross,
    place_grid_column,
    place_grid_tie_beam,
    place_member_between_points,
    place_wall_x_brace,
    place_x_brace_from_leg,
    update_member_profiles,
)
from schemas.model_edit import (
    DeleteMembersRequest,
    ModelEditBody,
    ModelEditResponse,
    PlaceBraceLegRequest,
    PlaceMemberBetweenPointsRequest,
    PlaceBracingCrossRequest,
    PlaceXBraceFromLegRequest,
    GroundPlacementNodesRequest,
    PlaceGridColumnRequest,
    PlaceGridTieBeamRequest,
    PlaceWallXBraceRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/api/model", tags=["model"])


class UpdateProfileBody(UpdateProfileRequest, ModelEditBody):
    pass


class DeleteMembersBody(DeleteMembersRequest, ModelEditBody):
    pass


class PlaceBraceLegBody(PlaceBraceLegRequest, ModelEditBody):
    pass


class PlaceMemberBetweenPointsBody(PlaceMemberBetweenPointsRequest, ModelEditBody):
    pass


class PlaceBracingCrossBody(PlaceBracingCrossRequest, ModelEditBody):
    pass


class PlaceXBraceFromLegBody(PlaceXBraceFromLegRequest, ModelEditBody):
    pass


class PlaceGridColumnBody(PlaceGridColumnRequest, ModelEditBody):
    pass


class PlaceGridTieBeamBody(PlaceGridTieBeamRequest, ModelEditBody):
    pass


class PlaceWallXBraceBody(PlaceWallXBraceRequest, ModelEditBody):
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


@router.post("/place-member-between-points", response_model=ModelEditResponse)
async def api_place_member_between_points(
    body: PlaceMemberBetweenPointsBody,
) -> ModelEditResponse:
    try:
        updated, changed = place_member_between_points(
            body.project_elements,
            start_mm=(body.start_mm.x, body.start_mm.y, body.start_mm.z),
            end_mm=(body.end_mm.x, body.end_mm.y, body.end_mm.z),
            profile=body.profile,
            assembly_id=body.assembly_id,
            element_type=body.element_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=changed,
        message=f"Placed {body.element_type.replace('_', ' ')} between picked nodes.",
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


@router.post("/place-x-brace-from-leg", response_model=ModelEditResponse)
async def api_place_x_brace_from_leg(body: PlaceXBraceFromLegBody) -> ModelEditResponse:
    try:
        updated, created = place_x_brace_from_leg(
            body.project_elements,
            start_mm=(body.start_mm.x, body.start_mm.y, body.start_mm.z),
            end_mm=(body.end_mm.x, body.end_mm.y, body.end_mm.z),
            start_element_id=body.start_element_id,
            end_element_id=body.end_element_id,
            profile=body.profile,
            assembly_id=body.assembly_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=f"Added full X-brace ({len(created)} members).",
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
            tie_location=body.tie_location,
            slope_side=body.slope_side,
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
            orientation=body.orientation,
            x_axis=body.x_axis,
            z_start=body.z_start,
            z_end=body.z_end,
            z_axis=body.z_axis,
            x_start=body.x_start,
            x_end=body.x_end,
            profile=body.profile,
            elevation=body.elevation,
            placement_label=body.placement_label,
            truss_chord=body.truss_chord,
            truss_type=body.truss_type,
            slope_side=body.slope_side,
            tie_location=body.tie_location,
            grid=body.grid,
            assembly_id=body.assembly_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=(
            f"Placed tie beam {body.profile} "
            + (
                f"on gable frame {body.z_axis} ({body.x_start} → {body.x_end}, {body.elevation})."
                if body.orientation == "along_x"
                else f"at {body.x_axis} ({body.z_start} → {body.z_end}, {body.elevation})."
            )
        ),
    )


@router.post("/place-wall-x-brace", response_model=ModelEditResponse)
async def api_place_wall_x_brace(body: PlaceWallXBraceBody) -> ModelEditResponse:
    try:
        updated, created = place_wall_x_brace(
            body.project_elements,
            wall_x=body.wall_x,
            bay_index=body.bay_index,
            panel_kind=body.panel_kind,
            frame_z=body.frame_z,
            z_start=body.z_start,
            z_end=body.z_end,
            x_start=body.x_start,
            x_end=body.x_end,
            elev_start=body.elev_start,
            elev_end=body.elev_end,
            slope_side=body.slope_side,
            brace_count=body.brace_count,
            profile=body.profile,
            assembly_id=body.assembly_id,
            grid=body.grid,
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    scope_label = body.scope.replace("_", " ")
    kind_label = "roof" if body.panel_kind == "roof" else "wall"
    return ModelEditResponse(
        projectElements=updated,
        changed_ids=created,
        message=(
            f"Added {kind_label} X-bracing ({len(created)} members, {scope_label})."
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
