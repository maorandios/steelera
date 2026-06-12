import {
  buildGableWallPanelsFromColumns,
  buildLongWallPanelsFromColumns,
} from "@/lib/bracing-panel-layout";
import { buildRoofPanels } from "@/lib/roof-panel-layout";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";
import type { TieBeamPanel } from "@/types/add-element";
import type { ProjectElementMm } from "@/types/project";

export function buildTieBeamPanels(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): TieBeamPanel[] {
  if (elements.length === 0) {
    return [];
  }
  const wallPanels: TieBeamPanel[] = [
    ...buildLongWallPanelsFromColumns(elements, grid),
    ...buildGableWallPanelsFromColumns(elements, grid),
  ];
  if (roofParams && roofParams.roof_style !== "flat") {
    return [...wallPanels, ...buildRoofPanels(grid, roofParams)];
  }
  return wallPanels;
}
