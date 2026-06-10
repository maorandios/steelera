import { parseMemberId } from "@/lib/selection-id-parse";
import type { SelectionContext } from "@/types/interaction";
import type { ProjectElementMm } from "@/types/project";

function matchesFrame(element: ProjectElementMm, frameZ: string): boolean {
  const parsed = parseMemberId(element.id);
  if (parsed.frameZ === frameZ) return true;
  if (element.id.includes(`-${frameZ}-`) || element.id.endsWith(`-${frameZ}`)) {
    return true;
  }
  return false;
}

function matchesTrussOnFrame(element: ProjectElementMm, frameZ: string): boolean {
  const et = element.element_type ?? "";
  if (!matchesFrame(element, frameZ)) return false;
  return (
    et === "truss_chord" ||
    et === "truss_web" ||
    /-truss-(?:TC|BC|web|post)-/.test(element.id)
  );
}

export function highlightIdsForSelection(
  ctx: SelectionContext,
  elements: ProjectElementMm[],
): string[] {
  if (ctx.highlightIds.length > 0) {
    return ctx.highlightIds;
  }
  return [ctx.elementId];
}

export function computeHighlightIds(
  element: ProjectElementMm,
  allElements: ProjectElementMm[],
): string[] {
  const parsed = parseMemberId(element.id);
  const et = element.element_type ?? element.shape_type;
  const ids = new Set<string>([element.id]);

  if (ctxIsBracing(element)) {
    return expandBracingHighlight(element, allElements);
  }

  if (
    parsed.frameZ &&
    (et === "truss_chord" ||
      et === "truss_web" ||
      /-truss-(?:TC|BC|web|post)-/.test(element.id))
  ) {
    return trussMemberIdsOnFrame(parsed.frameZ, allElements);
  }

  if (parsed.frameZ && (et === "column" || et === "rafter" || et === "haunch")) {
    for (const el of allElements) {
      if (matchesFrame(el, parsed.frameZ)) {
        ids.add(el.id);
      }
    }
    return [...ids];
  }

  if (et === "purlin") {
    for (const el of allElements) {
      if ((el.element_type ?? "") === "purlin") ids.add(el.id);
    }
    return [...ids];
  }

  if (et === "wall_girt") {
    for (const el of allElements) {
      if ((el.element_type ?? "") === "wall_girt") ids.add(el.id);
    }
    return [...ids];
  }

  return [element.id];
}

function ctxIsBracing(element: ProjectElementMm): boolean {
  const et = element.element_type ?? "";
  return et === "bracing" || et === "x_brace" || element.id.includes("-brace-");
}

function expandBracingHighlight(
  element: ProjectElementMm,
  allElements: ProjectElementMm[],
): string[] {
  const pairRe = /^(.+)-([ab])$/i;
  const m = element.id.match(pairRe);
  const ids = new Set<string>([element.id]);
  if (m) {
    const other = m[2].toLowerCase() === "a" ? `${m[1]}-b` : `${m[1]}-a`;
    if (allElements.some((e) => e.id === other)) {
      ids.add(other);
    }
  }
  return [...ids];
}

export function trussMemberIdsOnFrame(
  frameZ: string,
  elements: ProjectElementMm[],
): string[] {
  return elements
    .filter((el) => matchesTrussOnFrame(el, frameZ))
    .map((el) => el.id);
}

export function frameMemberIds(
  frameZ: string,
  elements: ProjectElementMm[],
): string[] {
  return elements.filter((el) => matchesFrame(el, frameZ)).map((el) => el.id);
}
