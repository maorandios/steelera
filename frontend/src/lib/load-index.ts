import type { SiteContext } from "@/types/site";

const GLOBAL_LOAD_FLOOR = 8.5;
const GLOBAL_CONSERVATISM_FACTOR = 1.1;
const MIN_DESIGN_WIND_MS_FOR_SIZING = 7.5;

/** Mirror backend `_effective_load` for UI disclosure (internal sizing floor). */
export function computeEffectiveLoadIndex(site: SiteContext): number {
  const terrainFactor: Record<string, number> = {
    "0": 1.25,
    II: 1.12,
    III: 1.0,
    IV: 0.92,
  };
  const tf = terrainFactor[site.terrain_class] ?? 1.0;
  const flooredDesign = Math.max(
    site.design_wind_proxy_ms,
    MIN_DESIGN_WIND_MS_FOR_SIZING,
  );
  const fromFlooredWind = flooredDesign * tf;
  return (
    Math.round(
      Math.max(
        site.load_index * GLOBAL_CONSERVATISM_FACTOR,
        fromFlooredWind * 0.98,
        GLOBAL_LOAD_FLOOR,
      ) * 100,
    ) / 100
  );
}
