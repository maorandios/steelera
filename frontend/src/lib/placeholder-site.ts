import type { SiteContext } from "@/types/site";

/** Mirrors backend `_default_site_context` — no external API calls. */
export function placeholderSiteContext(
  lat: number,
  lon: number,
  locationLabel: string,
): SiteContext {
  return {
    latitude: lat,
    longitude: lon,
    location_label: locationLabel,
    mean_wind_ms: 6.0,
    design_wind_proxy_ms: 8.5,
    terrain_class: "III",
    exposure: "open",
    load_index: 8.5,
    building_count_500m: 0,
    near_water: false,
    data_sources: ["pending"],
    surroundings_applied: "auto",
  };
}

export function isSiteClimatePending(site: SiteContext | null | undefined): boolean {
  return Boolean(site?.data_sources?.includes("pending"));
}
