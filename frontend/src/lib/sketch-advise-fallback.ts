import {
  classifyAngle,
  intentLabel,
  recognizeStructuralIntent,
  recommendProfiles,
} from "@/lib/structural-intent";
import { inferWallXBraceCorners, xBraceLegsAreDistinct } from "@/lib/brace-corners";
import type { ProjectElementMm } from "@/types/project";
import type {
  EnrichedSnapNode,
  SketchAnalysisResult,
  SketchApplyScope,
  StructuralIntentKind,
} from "@/types/sketch";
import type { OperationProposal } from "@/types/structural-advise";

const MULTI_PANEL_SLOPE_MM = 5500;

function profileOptions(spanMm: number, kind: StructuralIntentKind) {
  return recommendProfiles(spanMm, kind).map((profile, i) => ({
    profile,
    tier: i === 0 ? ("recommended" as const) : ("light" as const),
    tier_label: i === 0 ? "Optimal" : "Light",
    utilization: 0,
    governing: "span_rule",
  }));
}

function leg(start: EnrichedSnapNode, end: EnrichedSnapNode) {
  return {
    leg_start_mm: { x: start.x, y: start.y, z: start.z },
    leg_end_mm: { x: end.x, y: end.y, z: end.z },
  };
}

function bracingOperations(
  intent: SketchAnalysisResult["intent"],
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
  scope: SketchApplyScope,
  elements: ProjectElementMm[],
): OperationProposal[] {
  const span = intent.spanMm;
  const profiles = profileOptions(span, "bracing");
  const base = leg(start, end);
  const startPt = { x: start.x, y: start.y, z: start.z };
  const endPt = { x: end.x, y: end.y, z: end.z };
  const xCorners = inferWallXBraceCorners(
    startPt,
    endPt,
    elements,
    start.elementId,
    end.elementId,
  );
  const xCornersField =
    xCorners && xBraceLegsAreDistinct(xCorners)
      ? {
          x_corners_mm: xCorners.map((pt) => ({ x: pt.x, y: pt.y, z: pt.z })),
        }
      : {};
  const truss =
    /-truss-(tc|bc|web)/i.test(start.elementId) ||
    /-truss-(tc|bc|web)/i.test(end.elementId) ||
    start.elementType === "truss_chord" ||
    end.elementType === "truss_chord";
  const onColumn =
    /-col-/i.test(start.elementId) ||
    /-col-/i.test(end.elementId) ||
    start.elementType === "column" ||
    end.elementType === "column";
  const longSlope = span >= MULTI_PANEL_SLOPE_MM && truss && !onColumn;
  const panelCount = longSlope ? Math.max(2, Math.round(span / 4000)) : 1;

  const ops: OperationProposal[] = [];

  if (longSlope) {
    ops.push({
      id: "multi_panel_x",
      kind: "place_multi_panel_x",
      label: `${panelCount} X-braces on slope`,
      description: `Long truss slope (${Math.round(span).toLocaleString()} mm) — use multiple X-brace panels.`,
      recommended: true,
      element_kind: "bracing",
      scope_suggestion: "single",
      warnings: [],
      bracing_plane: "roof",
      panel_count: panelCount,
      profile_suggestions: profiles,
      ...base,
      ...xCornersField,
    });
  }

  ops.push({
    id: "full_x",
    kind: "place_x_brace",
    label: "Full X-brace",
    description:
      "Complete X-brace (both diagonals) — recommended for stability.",
    recommended: !longSlope,
    element_kind: "bracing",
    scope_suggestion: scope,
    warnings: [],
    bracing_plane: truss ? "roof" : "wall_long",
    panel_count: 1,
    profile_suggestions: profiles,
    ...base,
    ...xCornersField,
  });

  ops.push({
    id: "single_leg",
    kind: "place_single_member",
    label: "Single diagonal only",
    description: "Place exactly the line you drew (one brace leg).",
    recommended: false,
    element_kind: "bracing",
    scope_suggestion: scope,
    warnings: ["Single diagonal is tension-only — not a complete brace."],
    bracing_plane: truss ? "roof" : "wall_long",
    profile_suggestions: profiles,
    ...base,
  });

  return ops;
}

function memberOperations(
  kind: StructuralIntentKind,
  intent: SketchAnalysisResult["intent"],
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
  scope: SketchApplyScope,
): OperationProposal[] {
  const profiles = profileOptions(intent.spanMm, kind);
  const arrayKind = scope !== "single" ? "place_member_array" : "place_single_member";
  const labels: Record<string, string> = {
    tie_beam: "Place tie beam",
    purlin: "Place purlin",
    beam: "Place beam",
    unknown: "Place member",
  };
  return [
    {
      id: `place_${kind}`,
      kind: arrayKind,
      label: labels[kind] ?? labels.unknown,
      description: `Place ${intentLabel(kind).toLowerCase()} along the sketched span.`,
      recommended: true,
      element_kind: kind,
      scope_suggestion: scope,
      warnings: [],
      profile_suggestions: profiles,
      ...leg(start, end),
    },
  ];
}

/** Offline operation proposals when /api/structural/advise is unreachable. */
export function buildFallbackSketchAnalysis(
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
  elements: ProjectElementMm[],
  scope: SketchApplyScope = "single",
): SketchAnalysisResult {
  const intent = recognizeStructuralIntent(start, end, elements);
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = end.z - start.z;
  const angleClass = classifyAngle(dx, dy, dz);

  const isBracing =
    intent.kind === "bracing" ||
    (angleClass === "diagonal" &&
      (Math.abs(dz) > 500 || Math.abs(dx) > 500));

  const operations = isBracing
    ? bracingOperations(intent, start, end, scope, elements)
    : memberOperations(intent.kind, intent, start, end, scope);

  const rec = operations.find((o) => o.recommended) ?? operations[0];
  const profiles =
    rec?.profile_suggestions?.length
      ? rec.profile_suggestions
      : profileOptions(intent.spanMm, intent.kind);

  return {
    intent,
    profiles,
    message: `I detected a ${intent.label.toLowerCase()} (${Math.round(intent.spanMm).toLocaleString()} mm span).`,
    summary: `I detected a ${intent.label.toLowerCase()} (${Math.round(intent.spanMm).toLocaleString()} mm span). Choose how to place it.`,
    scope_suggestion: rec?.scope_suggestion ?? scope,
    scope_reason: "Offline advice — start the backend for full engineering analysis.",
    alternatives: [],
    ai_available: false,
    operations,
    recommended_operation_id: rec?.id ?? null,
  };
}
