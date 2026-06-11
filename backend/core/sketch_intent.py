"""Rule-based sketch intent classification with optional GPT refinement."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from core.env_loader import load_env
from core.spatial_context import format_project_context
from schemas.elements import ProjectElementMm
from schemas.site import SiteContext
from schemas.sketch import (
    AngleClass,
    SketchAnalyzeResponse,
    SketchIntentResult,
    SketchSnapNode,
    StructuralIntentKind,
)

load_env()

MODEL = "gpt-4o-mini"

HORIZONTAL_Y_TOL_MM = 250.0
LOW_EAVE_Y_MM = 2000.0
HIGH_ROOF_Y_MM = 3500.0

_INTENT_LABELS: dict[StructuralIntentKind, str] = {
    "tie_beam": "Tie Beam",
    "bracing": "Bracing",
    "purlin": "Purlin",
    "beam": "Beam",
    "unknown": "Structural Member",
}


@dataclass
class _GptIntent:
    kind: StructuralIntentKind
    confidence: float
    reasoning: str
    scope_suggestion: Literal["all_bays", "row", "single"] | None
    alternatives: list[StructuralIntentKind]
    ai_available: bool


def _client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _is_column(element: ProjectElementMm | None) -> bool:
    if element is None:
        return False
    if (element.element_type or "") == "column":
        return True
    return bool(re.search(r"-col-", element.id, re.I))


def _is_truss_member(element_id: str, element_type: str) -> bool:
    et = (element_type or "").lower()
    if et in ("truss_chord", "truss_web"):
        return True
    return bool(re.search(r"-truss-(tc|bc|web)", element_id, re.I))


def _element_for_node(
    elements: list[ProjectElementMm],
    node: SketchSnapNode,
) -> ProjectElementMm | None:
    for element in elements:
        if element.id == node.element_id:
            return element
    return None


def classify_angle(dx: float, dy: float, dz: float) -> AngleClass:
    horiz_len = math.hypot(dx, dz)
    vert_len = abs(dy)
    if horiz_len < 100 and vert_len > 300:
        return "vertical"
    if vert_len < HORIZONTAL_Y_TOL_MM and horiz_len > 300:
        return "horizontal"
    return "diagonal"


def classify_intent_rules(
    start: SketchSnapNode,
    end: SketchSnapNode,
    elements: list[ProjectElementMm],
) -> SketchIntentResult:
    dx = end.x - start.x
    dy = end.y - start.y
    dz = end.z - start.z
    span_mm = math.hypot(dx, dy, dz)
    angle_class = classify_angle(dx, dy, dz)

    start_el = _element_for_node(elements, start)
    end_el = _element_for_node(elements, end)
    low_start = start.y < LOW_EAVE_Y_MM
    low_end = end.y < LOW_EAVE_Y_MM
    high_start = start.y > HIGH_ROOF_Y_MM
    high_end = end.y > HIGH_ROOF_Y_MM

    base = {
        "angle_class": angle_class,
        "span_mm": round(span_mm, 1),
        "start_element_type": start.element_type,
        "end_element_type": end.element_type,
        "start_element_id": start.element_id,
        "end_element_id": end.element_id,
    }

    if (
        angle_class == "horizontal"
        and _is_column(start_el)
        and _is_column(end_el)
        and low_start
        and low_end
    ):
        return SketchIntentResult(
            **base,
            kind="tie_beam",
            label=_INTENT_LABELS["tie_beam"],
            confidence=0.88,
        )

    if angle_class == "diagonal":
        low = low_start or low_end
        high = high_start or high_end
        joint = (
            start.param_along_member in (0.0, 1.0)
            or end.param_along_member in (0.0, 1.0)
        )
        truss = _is_truss_member(start.element_id, start.element_type) or _is_truss_member(
            end.element_id, end.element_type
        )
        spans_bay = abs(end.z - start.z) > 500 or abs(end.x - start.x) > 500
        if (low and joint) or (high and (truss or joint)) or (joint and spans_bay):
            label = _INTENT_LABELS["bracing"]
            if high and truss:
                label = "Roof Bracing"
            return SketchIntentResult(
                **base,
                kind="bracing",
                label=label,
                confidence=0.85 if high and truss else 0.82,
            )

    if angle_class == "horizontal" and (high_start or high_end):
        return SketchIntentResult(
            **base,
            kind="purlin",
            label=_INTENT_LABELS["purlin"],
            confidence=0.76,
        )

    if angle_class == "horizontal":
        return SketchIntentResult(
            **base,
            kind="beam",
            label=_INTENT_LABELS["beam"],
            confidence=0.65,
        )

    if angle_class == "vertical":
        return SketchIntentResult(
            **base,
            kind="beam",
            label="Vertical Member",
            confidence=0.5,
        )

    return SketchIntentResult(
        **base,
        kind="unknown",
        label=_INTENT_LABELS["unknown"],
        confidence=0.4,
    )


def _suggest_scope(
    kind: StructuralIntentKind,
    start: SketchSnapNode,
    end: SketchSnapNode,
    z_coords_mm: list[float] | None,
) -> tuple[Literal["all_bays", "row", "single"], str]:
    z_count = len(z_coords_mm or [])
    spans_z = abs(end.z - start.z) > 100

    if kind == "tie_beam" and z_count >= 3 and spans_z:
        return (
            "all_bays",
            "Horizontal tie at eave level can repeat across matching bays.",
        )
    if kind == "purlin" and z_count >= 3:
        return (
            "all_bays",
            "Roof purlins typically repeat along the length at this level.",
        )
    if kind == "bracing":
        return (
            "row",
            "Bracing often repeats per frame line at similar joints.",
        )
    if kind == "beam" and z_count >= 3 and spans_z:
        return ("row", "Beam may repeat along the same grid row.")
    return ("single", "Place only at the sketched location.")


def _alternatives_for(kind: StructuralIntentKind) -> list[StructuralIntentKind]:
    all_kinds: list[StructuralIntentKind] = [
        "tie_beam",
        "bracing",
        "purlin",
        "beam",
    ]
    return [k for k in all_kinds if k != kind]


def _geometry_summary(
    intent: SketchIntentResult,
    start: SketchSnapNode,
    end: SketchSnapNode,
) -> dict[str, Any]:
    return {
        "span_mm": intent.span_mm,
        "angle_class": intent.angle_class,
        "start": {
            "element_id": start.element_id,
            "element_type": start.element_type,
            "y_mm": start.y,
            "z_mm": start.z,
            "tier": start.tier,
        },
        "end": {
            "element_id": end.element_id,
            "element_type": end.element_type,
            "y_mm": end.y,
            "z_mm": end.z,
            "tier": end.tier,
        },
        "rules_classification": {
            "kind": intent.kind,
            "confidence": intent.confidence,
            "label": intent.label,
        },
    }


def _gpt_classify_intent(
    *,
    elements: list[ProjectElementMm],
    start: SketchSnapNode,
    end: SketchSnapNode,
    rules_intent: SketchIntentResult,
) -> _GptIntent | None:
    client = _client()
    if client is None:
        return None

    spatial = format_project_context(elements)
    user_payload = json.dumps(
        {
            "sketch_geometry": _geometry_summary(rules_intent, start, end),
            "project_summary": spatial,
        },
        indent=2,
    )

    schema = {
        "type": "object",
        "properties": {
            "element_type": {
                "type": "string",
                "enum": ["tie_beam", "bracing", "purlin", "beam", "unknown"],
            },
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
            "scope_suggestion": {
                "type": "string",
                "enum": ["all_bays", "row", "single"],
            },
            "alternatives": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["tie_beam", "bracing", "purlin", "beam"],
                },
            },
        },
        "required": [
            "element_type",
            "confidence",
            "reasoning",
            "scope_suggestion",
            "alternatives",
        ],
        "additionalProperties": False,
    }

    system = (
        "You classify a sketched structural member in an existing steel shed model. "
        "Return JSON only. Valid element_type: tie_beam, bracing, purlin, beam, unknown. "
        "Do NOT output coordinates or profile names."
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_payload},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sketch_intent",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0.2,
        )
        raw: dict[str, Any] = json.loads(resp.choices[0].message.content or "{}")
        kind = str(raw.get("element_type", rules_intent.kind))
        if kind not in _INTENT_LABELS:
            kind = rules_intent.kind
        alts = [
            a
            for a in (raw.get("alternatives") or [])
            if a in _INTENT_LABELS and a != kind
        ]
        scope = raw.get("scope_suggestion")
        if scope not in ("all_bays", "row", "single"):
            scope = None
        return _GptIntent(
            kind=kind,  # type: ignore[arg-type]
            confidence=float(raw.get("confidence", rules_intent.confidence)),
            reasoning=str(raw.get("reasoning", "")),
            scope_suggestion=scope,  # type: ignore[arg-type]
            alternatives=alts,  # type: ignore[arg-type]
            ai_available=True,
        )
    except Exception:
        return None


def _merge_intent(
    rules: SketchIntentResult,
    gpt: _GptIntent | None,
    intent_override: StructuralIntentKind | None,
) -> tuple[SketchIntentResult, list[StructuralIntentKind], bool]:
    if intent_override is not None:
        return (
            rules.model_copy(
                update={
                    "kind": intent_override,
                    "label": _INTENT_LABELS[intent_override],
                    "confidence": 1.0,
                }
            ),
            _alternatives_for(intent_override),
            False,
        )

    if gpt is None or not gpt.ai_available:
        return rules, _alternatives_for(rules.kind), False

    if gpt.confidence >= rules.confidence:
        merged = rules.model_copy(
            update={
                "kind": gpt.kind,
                "label": _INTENT_LABELS.get(gpt.kind, rules.label),
                "confidence": round(min(gpt.confidence, 0.99), 2),
            }
        )
        alts = gpt.alternatives or _alternatives_for(merged.kind)
        return merged, alts, True

    return rules, _alternatives_for(rules.kind), True


def _profile_message(profiles: list) -> str:
    if not profiles:
        return ""
    rec = next((p for p in profiles if p.tier == "recommended"), profiles[0])
    util_pct = round(rec.utilization * 100)
    if util_pct > 0:
        return (
            f"{rec.profile} is the recommended pick "
            f"({util_pct}% utilization, {rec.governing})."
        )
    return f"{rec.profile} is the recommended pick for this span."


def _build_message(intent: SketchIntentResult, profiles: list, gpt: _GptIntent | None, ai_used: bool) -> str:
    if gpt and ai_used and gpt.reasoning:
        profile_note = _profile_message(profiles)
        if profile_note:
            return f"{gpt.reasoning} {profile_note}"
        return gpt.reasoning

    span = int(round(intent.span_mm))
    return (
        f"I detected a {intent.label.lower()} "
        f"({intent.angle_class}, {span:,} mm span)."
    )


def analyze_sketch_request(
    *,
    elements: list[ProjectElementMm],
    start: SketchSnapNode,
    end: SketchSnapNode,
    intent_override: StructuralIntentKind | None = None,
    shed_params: dict | None = None,
    site_context: SiteContext | None = None,
    z_coords_mm: list[float] | None = None,
) -> SketchAnalyzeResponse:
    from core.sketch_profiles import recommend_sketch_profiles

    rules = classify_intent_rules(start, end, elements)
    gpt = None if intent_override else _gpt_classify_intent(
        elements=elements,
        start=start,
        end=end,
        rules_intent=rules,
    )

    intent, alternatives, ai_used = _merge_intent(rules, gpt, intent_override)
    profiles = recommend_sketch_profiles(
        intent.kind,
        elements=elements,
        start=start,
        end=end,
        span_mm=intent.span_mm,
        shed_params=shed_params,
        site_context=site_context,
    )

    scope, scope_reason = _suggest_scope(intent.kind, start, end, z_coords_mm)
    if gpt and gpt.scope_suggestion and not intent_override:
        scope = gpt.scope_suggestion
        scope_reason = (
            f"AI suggests {scope.replace('_', ' ')} based on layout symmetry."
        )

    message = _build_message(intent, profiles, gpt, ai_used)

    return SketchAnalyzeResponse(
        intent=intent,
        profiles=profiles,
        message=message,
        scope_suggestion=scope,
        scope_reason=scope_reason,
        alternatives=alternatives,
        ai_available=bool(gpt and gpt.ai_available and not intent_override),
    )
