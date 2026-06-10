import {
  frameIndexFromZLabel,
  frameLabelFromIndex,
  isTrussMemberId,
  parseMemberId,
} from "@/lib/selection-id-parse";
import {
  computeHighlightIds,
  frameMemberIds,
  trussMemberIdsOnFrame,
} from "@/lib/selection-highlight";
import type { ProjectElementMm } from "@/types/project";
import type {
  BracingPlane,
  ParentAssembly,
  ProfileScope,
  SelectionContext,
} from "@/types/interaction";

const BRACE_PAIR_RE = /^(.+)-([ab])$/i;

function bracePairPrefix(id: string): string | null {
  const m = id.match(BRACE_PAIR_RE);
  return m ? m[1] : null;
}

function bracingPlaneFromId(id: string): BracingPlane {
  if (id.includes("-brace-roof-")) return "roof";
  if (id.includes("-brace-end-")) return "gable";
  if (/-brace-[AB]-/i.test(id)) return "wall_long";
  if (id.includes("-brace-custom-")) return "custom";
  return "unknown";
}

function bracingGroupKey(element: ProjectElementMm): string | null {
  const et = element.element_type ?? "";
  if (et !== "bracing" && et !== "x_brace" && !element.id.includes("-brace-")) {
    return null;
  }
  const plane = bracingPlaneFromId(element.id);
  if (plane !== "unknown") return `${plane}_bracing`;
  return et || "bracing";
}

function humanLabel(element: ProjectElementMm): string {
  const plane = bracingPlaneFromId(element.id);
  const et = element.element_type ?? element.shape_type;
  if (plane === "roof") return "Roof X-bracing";
  if (plane === "wall_long") return "Wall X-bracing";
  if (plane === "gable") return "Gable X-bracing";
  if (et === "bracing" || et === "x_brace") return "Bracing member";
  if (et === "column") return "Column";
  if (et === "rafter") return "Rafter";
  if (et === "purlin") return "Purlin";
  if (et === "wall_girt") return "Wall girt";
  if (et === "truss_chord") {
    if (element.id.includes("-truss-TC-")) return "Truss top chord";
    if (element.id.includes("-truss-BC-")) return "Truss bottom chord";
    return "Truss chord";
  }
  if (et === "truss_web") return "Truss web";
  if (et === "tie_beam") return "Tie beam";
  if (et === "haunch") return "Haunch";
  return et.replace(/_/g, " ");
}

function parentAssemblyFor(
  element: ProjectElementMm,
  parsed: ReturnType<typeof parseMemberId>,
): ParentAssembly {
  const et = element.element_type ?? "";
  if (
    et === "bracing" ||
    et === "x_brace" ||
    element.id.includes("-brace-")
  ) {
    return "bracing";
  }
  if (isTrussMemberId(element.id) || et === "truss_chord" || et === "truss_web") {
    return "truss";
  }
  if (et === "rafter" || et === "column" || et === "haunch") {
    return "frame";
  }
  if (et === "purlin") return "purlin_run";
  if (et === "wall_girt") return "girt_run";
  return "member";
}

function locationSubtitle(
  element: ProjectElementMm,
  parsed: ReturnType<typeof parseMemberId>,
  parentAssembly: ParentAssembly,
): string {
  const parts: string[] = [];
  const frameIdx = frameIndexFromZLabel(parsed.frameZ);
  if (frameIdx !== null) {
    parts.push(`Frame ${frameLabelFromIndex(frameIdx)}`);
  }
  if (parsed.gridX && parentAssembly === "frame") {
    parts.push(`Grid ${parsed.gridX}`);
  }
  if (parentAssembly === "truss" && parsed.frameZ) {
    parts.push("Truss");
  }
  if (parentAssembly === "purlin_run" && parsed.purlinIndex !== null) {
    parts.push(`Purlin ${parsed.purlinIndex + 1}`);
  }
  if (parentAssembly === "girt_run" && parsed.girtWall) {
    parts.push(`Wall ${parsed.girtWall}`);
  }
  if (parts.length === 0 && parsed.gridX) {
    parts.push(`Grid ${parsed.gridX}`);
  }
  return parts.join(" · ");
}

function defaultProfileScope(
  parentAssembly: ParentAssembly,
  isBracing: boolean,
): ProfileScope {
  if (isBracing) return "group";
  if (parentAssembly === "truss") return "truss";
  if (parentAssembly === "frame") return "frame";
  if (parentAssembly === "purlin_run" || parentAssembly === "girt_run") {
    return "element_type";
  }
  return "selection";
}

function isFrameTrussed(
  frameZ: string | null,
  allElements: ProjectElementMm[],
): boolean {
  if (!frameZ) return false;
  return trussMemberIdsOnFrame(frameZ, allElements).length > 0;
}

export function resolveSelectionContext(
  element: ProjectElementMm,
  allElements: ProjectElementMm[],
  options?: { trussType?: string | null },
): SelectionContext {
  const parsed = parseMemberId(element.id);
  const prefix = bracePairPrefix(element.id);
  const pairLeg = element.id.match(BRACE_PAIR_RE)?.[2]?.toLowerCase() ?? null;
  const groupKey = bracingGroupKey(element);
  const groupCount = groupKey
    ? allElements.filter((e) => bracingGroupKey(e) === groupKey).length
    : 0;

  let pairId: string | null = null;
  if (prefix && pairLeg) {
    const other = pairLeg === "a" ? `${prefix}-b` : `${prefix}-a`;
    if (allElements.some((e) => e.id === other)) {
      pairId = other;
    }
  }

  const et = element.element_type ?? "";
  const isBracing =
    et === "bracing" ||
    et === "x_brace" ||
    element.id.includes("-brace-");

  const parentAssembly = parentAssemblyFor(element, parsed);
  const frameIdx = frameIndexFromZLabel(parsed.frameZ);
  const highlightIds = computeHighlightIds(element);
  const frameTrussed = isFrameTrussed(parsed.frameZ, allElements);

  return {
    elementId: element.id,
    elementType: et || element.shape_type,
    profile: element.profile_name ?? null,
    label: humanLabel(element),
    locationSubtitle: locationSubtitle(element, parsed, parentAssembly),
    assemblyId: element.assembly_id ?? null,
    bracingPlane: isBracing ? bracingPlaneFromId(element.id) : null,
    pairId,
    pairPrefix: prefix,
    groupKey,
    groupCount,
    isBracing,
    parentAssembly,
    gridX: parsed.gridX,
    gridZ: parsed.frameZ,
    frameIndex: frameIdx,
    frameTrussed,
    trussType: options?.trussType ?? null,
    defaultProfileScope: defaultProfileScope(parentAssembly, isBracing),
    highlightIds,
    trussMemberCount: parsed.frameZ
      ? trussMemberIdsOnFrame(parsed.frameZ, allElements).length
      : 0,
    frameMemberCount: parsed.frameZ
      ? frameMemberIds(parsed.frameZ, allElements).length
      : 0,
  };
}
