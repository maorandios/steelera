"""Unified structural advisory — operation proposals from sketch or selection."""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any

from openai import OpenAI

from core.brace_geometry import estimate_roof_panel_count, infer_x_brace_corners
from core.env_loader import load_env
from core.sketch_intent import (
    HIGH_ROOF_Y_MM,
    LOW_EAVE_Y_MM,
    _alternatives_for,
    _suggest_scope,
    analyze_sketch_request,
    classify_intent_rules,
)
from core.sketch_profiles import recommend_sketch_profiles
from core.spatial_context import format_project_context
from schemas.chat import SelectionContextPayload
from schemas.elements import ProjectElementMm
from schemas.site import SiteContext
from schemas.sketch import SketchSnapNode, StructuralIntentKind
from schemas.structural_advise import (
    BracingPlane,
    OperationProposal,
    Point3Mm,
    StructuralAdviseRequest,
    StructuralAdviseResponse,
)

load_env()

MODEL = "gpt-4o-mini"
MULTI_PANEL_SLOPE_MM = 5500.0


def _pt(x: float, y: float, z: float) -> Point3Mm:
    return Point3Mm(x=x, y=y, z=z)


def _is_truss_member(element_id: str, element_type: str) -> bool:
    et = (element_type or "").lower()
    if et in ("truss_chord", "truss_web"):
        return True
    return bool(re.search(r"-truss-(tc|bc|web)", element_id, re.I))


def _is_column(element_id: str, element_type: str) -> bool:
    if (element_type or "") == "column":
        return True
    return bool(re.search(r"-col-", element_id, re.I))


def _bracing_plane(
    start: SketchSnapNode,
    end: SketchSnapNode,
) -> BracingPlane:
    if start.y > HIGH_ROOF_Y_MM or end.y > HIGH_ROOF_Y_MM:
        if _is_truss_member(start.element_id, start.element_type) or _is_truss_member(
            end.element_id, end.element_type
        ):
            return "roof"
        return "roof"
    if start.y < LOW_EAVE_Y_MM + 500 or end.y < LOW_EAVE_Y_MM + 500:
        return "wall_long"
    return "unknown"


def _sketch_operations(
    *,
    elements: list[ProjectElementMm],
    start: SketchSnapNode,
    end: SketchSnapNode,
    intent_kind: StructuralIntentKind,
    span_mm: float,
    angle_class: str,
    profiles: list,
    scope: str,
    shed_params: dict | None,
    site: SiteContext | None,
    z_coords_mm: list[float] | None,
) -> list[OperationProposal]:
    ops: list[OperationProposal] = []
    leg_start = _pt(start.x, start.y, start.z)
    leg_end = _pt(end.x, end.y, end.z)
    profile_payload = list(profiles)

    if intent_kind == "bracing" or (
        angle_class == "diagonal"
        and (start.y > LOW_EAVE_Y_MM or end.y > LOW_EAVE_Y_MM)
    ):
        plane = _bracing_plane(start, end)
        corners = infer_x_brace_corners(
            (start.x, start.y, start.z),
            (end.x, end.y, end.z),
            elements,
        )
        x_corners = None
        if corners:
            a, b, c, d = corners
            x_corners = [_pt(*a), _pt(*b), _pt(*c), _pt(*d)]

        slope_len = span_mm
        panel_count = 1
        if plane == "roof" and slope_len >= MULTI_PANEL_SLOPE_MM:
            from core.shed_params import DEFAULT_SHED_PARAMS, infer_shed_params_from_elements

            params = dict(DEFAULT_SHED_PARAMS)
            if shed_params:
                params.update(shed_params)
            elif elements:
                params.update(infer_shed_params_from_elements(elements))
            width = float(params.get("width", 12000.0))
            height = float(params.get("height", 6000.0))
            panel_count = estimate_roof_panel_count(
                slope_len, width_mm=width, height_mm=height
            )

        if panel_count > 1 and plane == "roof":
            ops.append(
                OperationProposal(
                    id="multi_panel_x",
                    kind="place_multi_panel_x",
                    label=f"{panel_count} X-braces on slope",
                    description=(
                        f"Long truss slope ({int(slope_len):,} mm) — "
                        f"{panel_count} full X-brace panels at truss nodes."
                    ),
                    recommended=True,
                    element_kind="bracing",
                    scope_suggestion="single",
                    warnings=[],
                    bracing_plane=plane,
                    panel_count=panel_count,
                    leg_start_mm=leg_start,
                    leg_end_mm=leg_end,
                    x_corners_mm=x_corners,
                    profile_suggestions=profile_payload,
                )
            )
            ops.append(
                OperationProposal(
                    id="full_x",
                    kind="place_x_brace",
                    label="Full X in this panel",
                    description="Complete X-brace (both diagonals) in the panel you sketched.",
                    recommended=False,
                    element_kind="bracing",
                    scope_suggestion=scope,  # type: ignore[arg-type]
                    warnings=[],
                    bracing_plane=plane,
                    panel_count=1,
                    leg_start_mm=leg_start,
                    leg_end_mm=leg_end,
                    x_corners_mm=x_corners,
                    profile_suggestions=profile_payload,
                )
            )
        else:
            ops.append(
                OperationProposal(
                    id="full_x",
                    kind="place_x_brace",
                    label="Full X-brace",
                    description=(
                        "Complete X-brace with both diagonals — "
                        "recommended for stability (single leg is tension-only)."
                    ),
                    recommended=True,
                    element_kind="bracing",
                    scope_suggestion=scope,  # type: ignore[arg-type]
                    bracing_plane=plane,
                    panel_count=1,
                    leg_start_mm=leg_start,
                    leg_end_mm=leg_end,
                    x_corners_mm=x_corners,
                    profile_suggestions=profile_payload,
                )
            )

        ops.append(
            OperationProposal(
                id="single_leg",
                kind="place_single_member",
                label="Single diagonal only",
                description="Place exactly the line you drew (one brace leg).",
                recommended=False,
                element_kind="bracing",
                scope_suggestion=scope,  # type: ignore[arg-type]
                warnings=["Single diagonal carries tension only — not a complete brace."],
                bracing_plane=plane,
                leg_start_mm=leg_start,
                leg_end_mm=leg_end,
                profile_suggestions=profile_payload,
            )
        )
        return ops

    if intent_kind in ("tie_beam", "beam"):
        ops.append(
            OperationProposal(
                id="place_beam",
                kind="place_member_array" if scope != "single" else "place_single_member",
                label="Place tie beam" if intent_kind == "tie_beam" else "Place beam",
                description="Place horizontal member along the sketched span.",
                recommended=True,
                element_kind=intent_kind,
                scope_suggestion=scope,  # type: ignore[arg-type]
                leg_start_mm=leg_start,
                leg_end_mm=leg_end,
                profile_suggestions=profile_payload,
            )
        )
        return ops

    if intent_kind == "purlin":
        ops.append(
            OperationProposal(
                id="place_purlin",
                kind="place_member_array" if scope != "single" else "place_single_member",
                label="Place purlin",
                description="Place purlin at roof level along the sketched line.",
                recommended=True,
                element_kind="purlin",
                scope_suggestion=scope,  # type: ignore[arg-type]
                leg_start_mm=leg_start,
                leg_end_mm=leg_end,
                profile_suggestions=profile_payload,
            )
        )
        return ops

    ops.append(
        OperationProposal(
            id="place_member",
            kind="place_single_member",
            label="Place member",
            description="Place a member along the sketched line.",
            recommended=True,
            element_kind=intent_kind,
            scope_suggestion="single",
            leg_start_mm=leg_start,
            leg_end_mm=leg_end,
            profile_suggestions=profile_payload,
        )
    )
    return ops


def _selection_operations(
    ctx: SelectionContextPayload,
    elements: list[ProjectElementMm],
    site: SiteContext | None,
    shed_params: dict | None,
) -> list[OperationProposal]:
    ops: list[OperationProposal] = []
    et = (ctx.element_type or "").lower()
    eid = ctx.element_id

    if et == "column" or _is_column(eid, et):
        profiles = recommend_sketch_profiles(
            "beam",
            elements=elements,
            start=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            end=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            span_mm=6000,
            shed_params=shed_params,
            site_context=site,
        )
        ops.append(
            OperationProposal(
                id="change_column_profile",
                kind="change_profile",
                label="Change column section",
                description=f"Upsize or downsize {ctx.profile or 'column'} with utilization check.",
                recommended=True,
                element_kind="beam",
                profile_suggestions=profiles,
            )
        )
        ops.append(
            OperationProposal(
                id="switch_to_truss",
                kind="switch_to_truss",
                label="Switch frame to truss",
                description="Replace portal rafters with a trussed roof on this frame.",
                recommended=False,
                element_kind="beam",
            )
        )
        return ops

    if et == "truss_chord" or "truss-tc" in eid.lower() or "truss-tc" in eid.lower():
        profiles = recommend_sketch_profiles(
            "beam",
            elements=elements,
            start=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            end=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            span_mm=8000,
            shed_params=shed_params,
            site_context=site,
        )
        ops.append(
            OperationProposal(
                id="change_truss_type",
                kind="change_truss_type",
                label="Change truss type",
                description="Switch pattern (Fink, queen-post, etc.) — rebuilds truss geometry.",
                recommended=True,
                element_kind="beam",
            )
        )
        ops.append(
            OperationProposal(
                id="change_chord_profile",
                kind="change_profile",
                label="Change chord section",
                description=f"Resize top/bottom chord from {ctx.profile or 'current'}.",
                recommended=False,
                element_kind="beam",
                profile_suggestions=profiles,
            )
        )
        ops.append(
            OperationProposal(
                id="switch_to_rafter",
                kind="switch_to_rafter",
                label="Switch to rafter frame",
                description="Replace truss with portal rafters on this frame.",
                recommended=False,
                element_kind="beam",
            )
        )
        return ops

    if et in ("bracing", "x_brace") or ctx.is_bracing:
        profiles = recommend_sketch_profiles(
            "bracing",
            elements=elements,
            start=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            end=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
            span_mm=4000,
            shed_params=shed_params,
            site_context=site,
        )
        ops.append(
            OperationProposal(
                id="change_brace_profile",
                kind="change_profile",
                label="Change bracing section",
                description="Update bracing profile with matching scope.",
                recommended=True,
                element_kind="bracing",
                profile_suggestions=profiles,
            )
        )
        return ops

    profiles = recommend_sketch_profiles(
        "unknown",
        elements=elements,
        start=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
        end=SketchSnapNode(x=0, y=0, z=0, element_id=eid, element_type=et),
        span_mm=5000,
        shed_params=shed_params,
        site_context=site,
    )
    ops.append(
        OperationProposal(
            id="change_profile",
            kind="change_profile",
            label="Change section size",
            description=f"Update profile for {ctx.label or 'this member'}.",
            recommended=True,
            element_kind="unknown",
            profile_suggestions=profiles,
        )
    )
    return ops


def _gpt_narrate_summary(
    *,
    elements: list[ProjectElementMm],
    operations: list[OperationProposal],
    fallback: str,
) -> tuple[str, bool]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback, False
    client = OpenAI(api_key=api_key)
    payload = {
        "operations": [
            {"id": o.id, "label": o.label, "description": o.description, "recommended": o.recommended}
            for o in operations
        ],
        "project_summary": format_project_context(elements)[:2000],
    }
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize structural operation options in 1-2 sentences for a mobile UI. "
                        "Recommend the best engineering choice. Do not output coordinates."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, indent=2)},
            ],
            temperature=0.2,
            max_tokens=120,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or fallback, True
    except Exception:
        return fallback, False


def advise_structural(request: StructuralAdviseRequest) -> StructuralAdviseResponse:
    elements = request.project_elements
    site = request.site_context

    if request.trigger == "selection" and request.selection_context:
        ctx = request.selection_context
        ops = _selection_operations(ctx, elements, site, request.shed_params)
        rec = next((o for o in ops if o.recommended), ops[0] if ops else None)
        profiles = rec.profile_suggestions if rec else []
        fallback = (
            f"Selected {ctx.label}. "
            + (rec.description if rec else "Choose an operation.")
        )
        summary, ai_ok = _gpt_narrate_summary(
            elements=elements, operations=ops, fallback=fallback
        )
        return StructuralAdviseResponse(
            summary=summary,
            operations=ops,
            recommended_operation_id=rec.id if rec else None,
            profiles=profiles,
            ai_available=ai_ok,
        )

    if not request.start_node or not request.end_node:
        return StructuralAdviseResponse(
            summary="Select two nodes or a member to get advice.",
            operations=[],
        )

    start = request.start_node
    end = request.end_node
    sketch = analyze_sketch_request(
        elements=elements,
        start=start,
        end=end,
        intent_override=request.intent_override,
        shed_params=request.shed_params,
        site_context=site,
        z_coords_mm=request.z_coords_mm,
    )
    intent = sketch.intent
    scope, scope_reason = _suggest_scope(
        intent.kind, start, end, request.z_coords_mm
    )
    if sketch.scope_suggestion:
        scope = sketch.scope_suggestion
        scope_reason = sketch.scope_reason

    ops = _sketch_operations(
        elements=elements,
        start=start,
        end=end,
        intent_kind=intent.kind,
        span_mm=intent.span_mm,
        angle_class=intent.angle_class,
        profiles=sketch.profiles,
        scope=scope,
        shed_params=request.shed_params,
        site=site,
        z_coords_mm=request.z_coords_mm,
    )
    rec = next((o for o in ops if o.recommended), ops[0] if ops else None)
    summary = sketch.message
    if rec and rec.kind in ("place_x_brace", "place_multi_panel_x"):
        summary = (
            f"{sketch.message} "
            f"Recommended: {rec.label} — {rec.description}"
        )

    return StructuralAdviseResponse(
        summary=summary,
        intent=intent,
        operations=ops,
        recommended_operation_id=rec.id if rec else None,
        profiles=sketch.profiles,
        scope_suggestion=scope,  # type: ignore[arg-type]
        scope_reason=scope_reason,
        alternatives=sketch.alternatives,
        ai_available=sketch.ai_available,
    )
