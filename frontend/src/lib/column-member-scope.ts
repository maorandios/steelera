import { parseMemberId } from "@/lib/selection-id-parse";
import type { ProjectElementMm } from "@/types/project";

export type ColumnEditScope = "selection" | "frame" | "element_type";

export type ColumnScopeChoice = ColumnEditScope | "pick_members";

export const COLUMN_SCOPE_OPTIONS: { scope: ColumnScopeChoice; label: string }[] =
  [
    { scope: "selection", label: "This member" },
    { scope: "frame", label: "This frame" },
    { scope: "element_type", label: "All columns" },
    { scope: "pick_members", label: "Pick members" },
  ];

function isColumn(element: ProjectElementMm): boolean {
  return (element.element_type ?? "") === "column";
}

export function resolveColumnTargetIds(
  elements: ProjectElementMm[],
  referenceElementId: string,
  scope: ColumnEditScope,
): string[] {
  const ref = elements.find((e) => e.id === referenceElementId);
  if (!ref || !isColumn(ref)) return [];

  if (scope === "selection") {
    return [referenceElementId];
  }

  if (scope === "element_type") {
    return elements.filter(isColumn).map((e) => e.id);
  }

  const frameZ = parseMemberId(referenceElementId).frameZ;
  if (!frameZ) {
    return [referenceElementId];
  }

  return elements
    .filter((e) => {
      if (!isColumn(e)) return false;
      return parseMemberId(e.id).frameZ === frameZ;
    })
    .map((e) => e.id);
}

export function describeColumnScopeCount(
  elements: ProjectElementMm[],
  referenceElementId: string,
  scope: ColumnEditScope,
): number {
  return resolveColumnTargetIds(elements, referenceElementId, scope).length;
}
