import { xPanelGridRefs, zPanelGridRefs } from "@/lib/bracing-panel-layout";
import { gridLineLetter, gridLineNumber } from "@/lib/structural-grid";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { RoofPanel, RoofSlopeSide } from "@/types/add-element";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";

export type RoofGeometryState = {
  style: ShedAssemblyParams["roof_style"];
  eaveY: number;
  ridgeX: number;
  ridgeY: number;
  monoHighSide: "A" | "B";
  originX: number;
  width: number;
};

export type RoofPanelCornerMm = {
  x: number;
  y: number;
  z: number;
};

export function computeRoofGeometry(
  grid: StructuralGridState,
  params: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  >,
): RoofGeometryState | null {
  if (params.roof_style === "flat" || grid.xCoordsMm.length < 2) {
    return null;
  }

  const originX = grid.xCoordsMm[0];
  const width = grid.xCoordsMm[grid.xCoordsMm.length - 1] - originX;
  if (width <= 0) return null;

  const eaveY = params.height;
  const pitchRad = (Math.max(0, params.roof_pitch_deg) * Math.PI) / 180;
  const monoHighSide = params.mono_high_side === "A" ? "A" : "B";

  if (params.roof_style === "mono_pitch") {
    const rise = width * Math.tan(pitchRad);
    const ridgeX = monoHighSide === "A" ? originX : originX + width;
    return {
      style: "mono_pitch",
      eaveY,
      ridgeX,
      ridgeY: eaveY + rise,
      monoHighSide,
      originX,
      width,
    };
  }

  const ridgeX = originX + width / 2;
  const rise = (width / 2) * Math.tan(pitchRad);
  return {
    style: "duo_pitch",
    eaveY,
    ridgeX,
    ridgeY: eaveY + rise,
    monoHighSide,
    originX,
    width,
  };
}

export function roofElevationAtX(roof: RoofGeometryState, xMm: number): number {
  if (roof.style === "mono_pitch") {
    const lowX = roof.monoHighSide === "A" ? roof.originX + roof.width : roof.originX;
    const highX = roof.monoHighSide === "A" ? roof.originX : roof.originX + roof.width;
    const span = Math.abs(highX - lowX);
    if (span < 1) return roof.eaveY;
    const t = Math.max(0, Math.min(1, Math.abs(xMm - lowX) / span));
    return roof.eaveY + t * (roof.ridgeY - roof.eaveY);
  }

  const leftX = roof.originX;
  const rightX = roof.originX + roof.width;
  if (xMm <= roof.ridgeX) {
    const span = roof.ridgeX - leftX;
    if (span < 1) return roof.ridgeY;
    const t = (xMm - leftX) / span;
    return roof.eaveY + t * (roof.ridgeY - roof.eaveY);
  }
  const span = rightX - roof.ridgeX;
  if (span < 1) return roof.ridgeY;
  const t = (xMm - roof.ridgeX) / span;
  return roof.ridgeY + t * (roof.eaveY - roof.ridgeY);
}

function ridgeGridLabel(
  grid: StructuralGridState,
  roof: RoofGeometryState,
): string {
  if (roof.style === "mono_pitch") {
    const idx =
      roof.monoHighSide === "A" ? 0 : Math.max(0, grid.xCoordsMm.length - 1);
    return gridLineLetter(idx);
  }
  const [label] = xPanelGridRefs(roof.ridgeX, roof.ridgeX, grid);
  return label;
}

function isEaveAtX(roof: RoofGeometryState, xMm: number): boolean {
  return Math.abs(roofElevationAtX(roof, xMm) - roof.eaveY) < 50;
}

export type RoofSlopeSegment = {
  slopeSide: RoofSlopeSide;
  slopeIndex: number;
  xStart: string;
  xEnd: string;
  x0Mm: number;
  x1Mm: number;
  elevStart: string;
  elevEnd: string;
};

export function roofSlopeSegments(
  grid: StructuralGridState,
  roof: RoofGeometryState,
): RoofSlopeSegment[] {
  const left = gridLineLetter(0);
  const right = gridLineLetter(Math.max(0, grid.xCoordsMm.length - 1));
  const leftMm = grid.xCoordsMm[0];
  const rightMm = grid.xCoordsMm[grid.xCoordsMm.length - 1];

  if (roof.style === "mono_pitch") {
    const [xStart, xEnd] = xPanelGridRefs(leftMm, rightMm, grid);
    return [
      {
        slopeSide: "mono",
        slopeIndex: 0,
        xStart,
        xEnd,
        x0Mm: leftMm,
        x1Mm: rightMm,
        elevStart: isEaveAtX(roof, leftMm) ? "eave" : "roof",
        elevEnd: isEaveAtX(roof, rightMm) ? "eave" : "roof",
      },
    ];
  }

  const ridge = ridgeGridLabel(grid, roof);
  const ridgeMm = roof.ridgeX;
  const [leftStart, leftEnd] = xPanelGridRefs(leftMm, ridgeMm, grid);
  const [rightStart, rightEnd] = xPanelGridRefs(ridgeMm, rightMm, grid);
  return [
    {
      slopeSide: "left",
      slopeIndex: 0,
      xStart: leftStart,
      xEnd: leftEnd,
      x0Mm: leftMm,
      x1Mm: ridgeMm,
      elevStart: "eave",
      elevEnd: "apex",
    },
    {
      slopeSide: "right",
      slopeIndex: 1,
      xStart: rightStart,
      xEnd: rightEnd,
      x0Mm: ridgeMm,
      x1Mm: rightMm,
      elevStart: "apex",
      elevEnd: "eave",
    },
  ];
}

export function resolveRoofNodeMm(
  roof: RoofGeometryState,
  grid: StructuralGridState,
  xLabel: string,
  zMm: number,
  elevation: string,
): RoofPanelCornerMm {
  const xIdx = grid.xCoordsMm.findIndex((_, i) => gridLineLetter(i) === xLabel);
  let xMm = xIdx >= 0 ? grid.xCoordsMm[xIdx] : roof.originX;
  if (xLabel.includes("+")) {
    const [base, frac] = xLabel.split("+");
    const baseIdx = grid.xCoordsMm.findIndex(
      (_, i) => gridLineLetter(i) === base,
    );
    if (baseIdx >= 0 && baseIdx < grid.xCoordsMm.length - 1) {
      const m = frac.match(/^(\d+)\/(\d+)$/);
      if (m) {
        const a = grid.xCoordsMm[baseIdx];
        const b = grid.xCoordsMm[baseIdx + 1];
        xMm = a + ((Number(m[1]) / Number(m[2])) * (b - a));
      }
    }
  }

  const elev = elevation.toLowerCase();
  let yMm = roof.eaveY;
  if (elev === "ground") {
    yMm = 0;
  } else if (elev === "apex" || elev === "ridge") {
    yMm = roof.ridgeY;
  } else if (elev === "roof") {
    yMm = roofElevationAtX(roof, xMm);
  } else if (elev === "eave") {
    yMm = roof.eaveY;
  } else {
    yMm = roofElevationAtX(roof, xMm);
  }

  return { x: xMm, y: yMm, z: zMm };
}

export function roofPanelCornersMm(
  panel: RoofPanel,
  grid: StructuralGridState,
  roof: RoofGeometryState,
): [RoofPanelCornerMm, RoofPanelCornerMm, RoofPanelCornerMm, RoofPanelCornerMm] {
  const low = resolveRoofNodeMm(roof, grid, panel.xStart, panel.z0Mm, panel.elevStart);
  const high = resolveRoofNodeMm(roof, grid, panel.xEnd, panel.z0Mm, panel.elevEnd);
  const highFar = resolveRoofNodeMm(roof, grid, panel.xEnd, panel.z1Mm, panel.elevEnd);
  const lowFar = resolveRoofNodeMm(roof, grid, panel.xStart, panel.z1Mm, panel.elevStart);
  return [low, lowFar, high, highFar];
}

export function buildRoofPanels(
  grid: StructuralGridState,
  params: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  >,
): RoofPanel[] {
  const roof = computeRoofGeometry(grid, params);
  if (!roof || grid.zCoordsMm.length < 2) {
    return [];
  }

  const slopes = roofSlopeSegments(grid, roof);
  const out: RoofPanel[] = [];

  for (let bayIndex = 0; bayIndex < grid.zCoordsMm.length - 1; bayIndex += 1) {
    const z0Mm = grid.zCoordsMm[bayIndex];
    const z1Mm = grid.zCoordsMm[bayIndex + 1];
    const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);

    for (const slope of slopes) {
      const slopeLabel =
        slope.slopeSide === "left"
          ? "Left slope"
          : slope.slopeSide === "right"
            ? "Right slope"
            : "Roof slope";
      out.push({
        kind: "roof",
        slopeSide: slope.slopeSide,
        slopeIndex: slope.slopeIndex,
        bayIndex,
        zStart,
        zEnd,
        z0Mm,
        z1Mm,
        xStart: slope.xStart,
        xEnd: slope.xEnd,
        x0Mm: slope.x0Mm,
        x1Mm: slope.x1Mm,
        elevStart: slope.elevStart,
        elevEnd: slope.elevEnd,
        label: `${slopeLabel} · Frame ${zStart} → ${zEnd}`,
      });
    }
  }

  return out;
}
