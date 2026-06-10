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

/** Viewport pick highlight — single member only (bulk scopes use action bar, not pick). */
export function computeHighlightIds(element: ProjectElementMm): string[] {
  return [element.id];
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
