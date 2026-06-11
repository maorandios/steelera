import { SHED_ASSEMBLY_ID } from "@/lib/shed-assembly";
import {
  gridLineLetter,
  gridLineNumber,
  type StructuralGridState,
} from "@/lib/structural-grid";
import type { GridPlacementContext, GridSelectionContext } from "@/types/grid-selection";
import type { ProjectElementMm } from "@/types/project";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";

const DEFAULT_COLUMN = "HEA200";
const DEFAULT_TIE = "IPE200";

export function gridBayId(bayIndex: number): string {
  return `grid:bay:${bayIndex}`;
}

export function gridFrameId(frameIndex: number): string {
  return `grid:frame:${frameIndex}`;
}

export function parseGridSelectionId(
  gridId: string,
): { kind: "bay" | "frame"; index: number } | null {
  const bay = gridId.match(/^grid:bay:(\d+)$/);
  if (bay) {
    return { kind: "bay", index: Number(bay[1]) };
  }
  const frame = gridId.match(/^grid:frame:(\d+)$/);
  if (frame) {
    return { kind: "frame", index: Number(frame[1]) };
  }
  return null;
}

export function xLabelsForGrid(grid: StructuralGridState): string[] {
  return grid.xCoordsMm.map((_, i) => gridLineLetter(i));
}

export function zLabelsForGrid(grid: StructuralGridState): string[] {
  return grid.zCoordsMm.map((_, i) => gridLineNumber(i));
}

export function inferTrussedZLabels(
  elements: ProjectElementMm[],
  zLabels: string[],
  useTruss: boolean,
): string[] {
  if (useTruss) {
    return [...zLabels];
  }
  const trussed = new Set<string>();
  for (const element of elements) {
    const m = element.id.match(/-truss-(?:TC|BC|web|post)-(\d+)/);
    if (m) {
      trussed.add(m[1]);
    }
  }
  return [...trussed];
}

export function defaultColumnProfile(elements: ProjectElementMm[]): string {
  const col = elements.find((e) => e.element_type === "column" && e.profile_name);
  return col?.profile_name ?? DEFAULT_COLUMN;
}

export function defaultTieProfile(elements: ProjectElementMm[]): string {
  const tie = elements.find((e) => e.element_type === "tie_beam" && e.profile_name);
  return tie?.profile_name ?? DEFAULT_TIE;
}

export function shedParamsToGridPlacement(
  params: ShedAssemblyParams,
): GridPlacementContext {
  return {
    x_spans: params.x_spans,
    z_spans: params.z_spans,
    height_mm: params.height,
    roof_pitch_deg: params.roof_pitch_deg,
    roof_style: params.roof_style,
    mono_high_side: params.mono_high_side ?? "B",
  };
}

/** Grid context from viewport cumulative coords (matches panel pick refs). */
export function gridPlacementFromStructuralGrid(
  grid: StructuralGridState,
  params: Pick<
    ShedAssemblyParams,
    "height" | "roof_pitch_deg" | "roof_style" | "mono_high_side"
  >,
): GridPlacementContext {
  const xSpans: number[] = [];
  for (let i = 1; i < grid.xCoordsMm.length; i += 1) {
    xSpans.push(grid.xCoordsMm[i] - grid.xCoordsMm[i - 1]);
  }
  const zSpans: number[] = [];
  for (let i = 1; i < grid.zCoordsMm.length; i += 1) {
    zSpans.push(grid.zCoordsMm[i] - grid.zCoordsMm[i - 1]);
  }
  return {
    x_spans: xSpans.length > 0 ? xSpans : [15000],
    z_spans: zSpans.length > 0 ? zSpans : [10000],
    height_mm: params.height,
    roof_pitch_deg: params.roof_pitch_deg,
    roof_style: params.roof_style,
    mono_high_side: params.mono_high_side ?? "B",
  };
}

export function resolveBaySelection(
  bayIndex: number,
  grid: StructuralGridState,
  elements: ProjectElementMm[],
  params: ShedAssemblyParams | null,
): GridSelectionContext | null {
  const zCount = grid.zCoordsMm.length;
  if (bayIndex < 0 || bayIndex >= zCount - 1) {
    return null;
  }
  const zStart = gridLineNumber(bayIndex);
  const zEnd = gridLineNumber(bayIndex + 1);
  const xLabels = xLabelsForGrid(grid);
  const bayLengthMm = Math.round(
    grid.zCoordsMm[bayIndex + 1] - grid.zCoordsMm[bayIndex],
  );

  return {
    kind: "bay",
    gridId: gridBayId(bayIndex),
    label: `Bay ${zStart} → ${zEnd}`,
    subtitle: `${bayLengthMm} mm · ${xLabels.length} grid lines`,
    bayIndex,
    frameIndex: null,
    zStart,
    zEnd,
    xLabels,
    defaultColumnProfile: defaultColumnProfile(elements),
    defaultTieProfile: defaultTieProfile(elements),
  };
}

export function resolveFrameSelection(
  frameIndex: number,
  grid: StructuralGridState,
  elements: ProjectElementMm[],
): GridSelectionContext | null {
  if (frameIndex < 0 || frameIndex >= grid.zCoordsMm.length) {
    return null;
  }
  const zLabel = gridLineNumber(frameIndex);
  const xLabels = xLabelsForGrid(grid);
  const zMm = grid.zCoordsMm[frameIndex];

  return {
    kind: "frame",
    gridId: gridFrameId(frameIndex),
    label: `Frame ${zLabel}`,
    subtitle: `Z = ${Math.round(zMm)} mm`,
    bayIndex: null,
    frameIndex,
    zStart: zLabel,
    zEnd: zLabel,
    xLabels,
    defaultColumnProfile: defaultColumnProfile(elements),
    defaultTieProfile: defaultTieProfile(elements),
  };
}

/** Mid-bay Z sub-node between two frame labels (e.g. 2+1/2). */
export function midBayZLabel(zStart: string, zEnd: string): string {
  return `${zStart}+1/2`;
}

export function columnsInBay(
  elements: ProjectElementMm[],
  zStart: string,
  zEnd: string,
  xLabels: string[],
): ProjectElementMm[] {
  const zTokens = new Set([zStart, zEnd, midBayZLabel(zStart, zEnd)]);
  return elements.filter((e) => {
    if (e.element_type !== "column") return false;
    const m = e.id.match(/-col-([A-Z]+)-(.+)$/);
    if (!m) return false;
    const [, x, zToken] = m;
    if (!xLabels.includes(x)) return false;
    const decoded = zToken.replace(/p/g, "+").replace(/_/g, "/");
    if (zTokens.has(decoded) || zTokens.has(zToken)) return true;
    return decoded === zStart || decoded === zEnd;
  });
}

export function assemblyIdFromElements(elements: ProjectElementMm[]): string {
  const hit = elements.find((e) => e.assembly_id);
  return hit?.assembly_id ?? SHED_ASSEMBLY_ID;
}
