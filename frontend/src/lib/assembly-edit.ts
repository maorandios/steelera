import {
  formatSpansInput,
  totalFromSpans,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import { assemblyParamsToShedConfig } from "@/lib/shed-config";
import type { ShedAssemblyConfig, ShedBayConfiguration, TrussType } from "@/types/shed-config";

function defaultBays(config: ShedAssemblyConfig): ShedBayConfiguration[] {
  const n = config.grid_layout.z_spans.length;
  return Array.from({ length: n }, (_, bay_index) => ({
    bay_index,
    use_truss: false,
    truss_type: "none" as const,
    x_bracing_left_wall: Boolean(config.gable_bracing),
    x_bracing_right_wall: Boolean(config.gable_bracing),
    wall_girts: true,
    sag_rods: false,
  }));
}

function mergedBays(config: ShedAssemblyConfig): ShedBayConfiguration[] {
  const base = defaultBays(config);
  const byIndex = new Map(
    config.bays_configuration.map((b) => [b.bay_index, b]),
  );
  return base.map((b) => byIndex.get(b.bay_index) ?? b);
}

function withBays(
  config: ShedAssemblyConfig,
  bays: ShedBayConfiguration[],
): ShedAssemblyConfig {
  return { ...config, bays_configuration: bays };
}

function patchAdjacentBaysForFrame(
  bays: ShedBayConfiguration[],
  frameIndex: number,
  patch: Partial<ShedBayConfiguration>,
): ShedBayConfiguration[] {
  const nBays = bays.length;
  const indices = new Set<number>();
  if (frameIndex > 0) indices.add(frameIndex - 1);
  if (frameIndex < nBays) indices.add(frameIndex);
  return bays.map((bay) =>
    indices.has(bay.bay_index) ? { ...bay, ...patch } : bay,
  );
}

export function configFromParams(params: ShedAssemblyParams): ShedAssemblyConfig {
  return assemblyParamsToShedConfig(params);
}

export function applyTrussTypeToFrame(
  params: ShedAssemblyParams,
  frameIndex: number,
  trussType: Exclude<TrussType, "none">,
): ShedAssemblyConfig {
  const config = configFromParams(params);
  const bays = patchAdjacentBaysForFrame(mergedBays(config), frameIndex, {
    use_truss: true,
    truss_type: trussType,
  });
  return withBays(config, bays);
}

export function applyTrussTypeGlobally(
  params: ShedAssemblyParams,
  trussType: Exclude<TrussType, "none">,
): ShedAssemblyConfig {
  const config = configFromParams(params);
  const bays = mergedBays(config).map((bay) => ({
    ...bay,
    use_truss: true,
    truss_type: trussType,
  }));
  return withBays(config, bays);
}

export function switchFrameToTruss(
  params: ShedAssemblyParams,
  frameIndex: number,
): ShedAssemblyConfig {
  const trussType = params.use_truss ? params.truss_type : "pratt";
  return applyTrussTypeToFrame(params, frameIndex, trussType);
}

export function switchFrameToRafter(
  params: ShedAssemblyParams,
  frameIndex: number,
): ShedAssemblyConfig {
  const config = configFromParams(params);
  const bays = patchAdjacentBaysForFrame(mergedBays(config), frameIndex, {
    use_truss: false,
    truss_type: "none",
  });
  return withBays(config, bays);
}

export function insertFrameAfter(
  params: ShedAssemblyParams,
  afterBayIndex: number,
): ShedAssemblyParams {
  const spans = [...params.z_spans];
  const ref =
    spans[afterBayIndex] ??
    spans[spans.length - 1] ??
    6_000;
  const insertAt = Math.min(Math.max(afterBayIndex + 1, 0), spans.length);
  spans.splice(insertAt, 0, ref);
  return {
    ...params,
    z_spans: spans,
    z_spans_input: formatSpansInput(spans),
    length: totalFromSpans(spans),
  };
}

export function removeFrameAt(
  params: ShedAssemblyParams,
  frameIndex: number,
): ShedAssemblyParams | null {
  const nFrames = params.z_spans.length + 1;
  if (nFrames <= 2) return null;
  const spans = [...params.z_spans];
  if (frameIndex <= 0) {
    spans.shift();
  } else if (frameIndex >= nFrames - 1) {
    spans.pop();
  } else {
    const merged = spans[frameIndex - 1] + spans[frameIndex];
    spans.splice(frameIndex - 1, 2, merged);
  }
  return {
    ...params,
    z_spans: spans,
    z_spans_input: formatSpansInput(spans),
    length: totalFromSpans(spans),
  };
}

/** Bay index after which to insert when adding a frame beside the selected frame line. */
export function insertBayIndexForFrame(frameIndex: number, zSpanCount: number): number {
  if (frameIndex < 0) return zSpanCount - 1;
  if (frameIndex >= zSpanCount) return zSpanCount - 1;
  return frameIndex;
}
