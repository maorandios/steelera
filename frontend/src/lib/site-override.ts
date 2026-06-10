import type { SiteContext } from "@/types/site";
import type { SiteSurroundings } from "@/lib/site-surroundings";

function terrainLoadFactor(terrainClass: string, nearWater: boolean): number {
  const factors: Record<string, number> = {
    "0": 1.25,
    II: 1.12,
    III: 1.0,
    IV: 0.92,
  };
  let base = factors[terrainClass] ?? 1.0;
  if (nearWater && terrainClass !== "IV") {
    base = Math.max(base, 1.15);
  }
  return base;
}

/** Mirror backend `apply_surroundings_override` — no external API calls. */
export function applySiteSurroundingsOverride(
  ctx: SiteContext,
  surroundings: SiteSurroundings,
): SiteContext {
  if (surroundings === "auto") {
    return { ...ctx, surroundings_applied: "auto" };
  }

  const detectedTerrain = ctx.detected_terrain_class ?? ctx.terrain_class;
  const detectedLoad = ctx.detected_load_index ?? ctx.load_index;
  const sources = [...ctx.data_sources];

  if (surroundings === "open_industrial") {
    const terrain = "II" as const;
    const exposure = "open" as const;
    sources.push("override:open_industrial");
    let loadIndex =
      Math.round(ctx.design_wind_proxy_ms * terrainLoadFactor(terrain, ctx.near_water) * 100) /
      100;
    if (loadIndex < 9.0) {
      loadIndex = Math.max(loadIndex, 9.0);
    }
    return {
      ...ctx,
      terrain_class: terrain,
      exposure,
      load_index: loadIndex,
      data_sources: sources,
      detected_terrain_class: detectedTerrain,
      detected_load_index: detectedLoad,
      surroundings_applied: surroundings,
    };
  }

  if (surroundings === "built_up") {
    const terrain = (ctx.building_count_500m >= 12 ? "IV" : "III") as SiteContext["terrain_class"];
    const exposure = "sheltered" as const;
    sources.push("override:built_up");
    const loadIndex =
      Math.round(ctx.design_wind_proxy_ms * terrainLoadFactor(terrain, ctx.near_water) * 100) /
      100;
    return {
      ...ctx,
      terrain_class: terrain,
      exposure,
      load_index: loadIndex,
      data_sources: sources,
      detected_terrain_class: detectedTerrain,
      detected_load_index: detectedLoad,
      surroundings_applied: surroundings,
    };
  }

  return ctx;
}
