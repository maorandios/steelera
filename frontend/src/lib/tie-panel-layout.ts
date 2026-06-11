import {
  buildGableWallPanelsFromColumns,
  buildLongWallPanelsFromColumns,
} from "@/lib/bracing-panel-layout";
import {
  buildTrussBcPanels,
  buildTrussTcPanels,
} from "@/lib/truss-panel-layout";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { TieBeamPanel } from "@/types/add-element";
import type { ProjectElementMm } from "@/types/project";

export function buildTieBeamPanels(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): TieBeamPanel[] {
  if (elements.length === 0) {
    return [];
  }
  return [
    ...buildLongWallPanelsFromColumns(elements, grid),
    ...buildGableWallPanelsFromColumns(elements, grid),
    ...buildTrussTcPanels(elements, grid),
    ...buildTrussBcPanels(elements, grid),
  ];
}
