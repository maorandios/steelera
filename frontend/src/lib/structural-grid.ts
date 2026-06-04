import type { ShedAssemblyParams } from "@/lib/shed-assembly";

/** Structural CAD grid: cumulative bay coordinates from comma-separated spacings (mm). */

export interface StructuralGridState {
  /** Comma-separated bay spacings along world X (mm). */
  xSpacingInput: string;
  /** Comma-separated bay spacings along world Z / plan depth (mm). */
  zSpacingInput: string;
  xCoordsMm: number[];
  zCoordsMm: number[];
}

export const DEFAULT_STRUCTURAL_GRID: StructuralGridState = {
  xSpacingInput: "3000, 7000, 10000, 5000",
  zSpacingInput: "5000, 5000, 5000, 5000, 5000, 5000",
  xCoordsMm: [0, 3000, 10000, 20000, 25000],
  zCoordsMm: [0, 5000, 10000, 15000, 20000, 25000, 30000],
};

/**
 * Parse "6000, 6000" → cumulative [0, 6000, 12000] (mm).
 * Each token is a bay width/depth increment, not an absolute coordinate.
 */
export function parseCumulativeSpacingMm(input: string): number[] {
  const tokens = input
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (tokens.length === 0) {
    return [0];
  }

  const coords: number[] = [0];
  let cumulative = 0;

  for (const token of tokens) {
    const step = Number(token);
    if (!Number.isFinite(step) || step <= 0) {
      continue;
    }
    cumulative += step;
    coords.push(Math.round(cumulative * 1000) / 1000);
  }

  return coords;
}

export function buildStructuralGridState(
  xSpacingInput: string,
  zSpacingInput: string,
): StructuralGridState {
  return {
    xSpacingInput,
    zSpacingInput,
    xCoordsMm: parseCumulativeSpacingMm(xSpacingInput),
    zCoordsMm: parseCumulativeSpacingMm(zSpacingInput),
  };
}

/**
 * Portal frame Z positions — mirrors backend `geometry_engine._frame_positions_along`.
 */
export function framePositionsAlongMm(
  lengthMm: number,
  spacingMm: number,
): number[] {
  const positions: number[] = [];
  let z = 0;

  while (z <= lengthMm + 1e-6) {
    positions.push(Math.round(z * 1000) / 1000);
    if (z >= lengthMm - 1e-6) {
      break;
    }
    z += spacingMm;
  }

  if (positions.length > 0 && positions[positions.length - 1] < lengthMm - 1e-6) {
    positions.push(Math.round(lengthMm * 1000) / 1000);
  }

  return positions;
}

/** Bay increments between consecutive frame lines (for grid Z spacing input). */
export function baySpacingsFromFramePositions(framePositionsMm: number[]): number[] {
  const spacings: number[] = [];
  for (let i = 1; i < framePositionsMm.length; i += 1) {
    spacings.push(
      Math.round((framePositionsMm[i] - framePositionsMm[i - 1]) * 1000) / 1000,
    );
  }
  return spacings;
}

/** Grid strings mirror shed span inputs exactly. */
export function gridInputsFromShedParams(
  params: Pick<ShedAssemblyParams, "x_spans_input" | "z_spans_input">,
): { xSpacingInput: string; zSpacingInput: string } {
  return {
    xSpacingInput: params.x_spans_input,
    zSpacingInput: params.z_spans_input,
  };
}

export function structuralGridFromShedParams(
  params: Pick<ShedAssemblyParams, "x_spans_input" | "z_spans_input">,
): StructuralGridState {
  const { xSpacingInput, zSpacingInput } = gridInputsFromShedParams(params);
  return buildStructuralGridState(xSpacingInput, zSpacingInput);
}

/** Grid line labels: A, B, C … (X-direction lines). */
export function gridLineLetter(index: number): string {
  if (index < 0) return "?";
  if (index < 26) {
    return String.fromCharCode(65 + index);
  }
  const first = Math.floor(index / 26) - 1;
  const second = index % 26;
  return (
    String.fromCharCode(65 + first) + String.fromCharCode(65 + second)
  );
}

/** Grid line labels: 1, 2, 3 … (Z-direction lines). */
export function gridLineNumber(index: number): string {
  return String(index + 1);
}
