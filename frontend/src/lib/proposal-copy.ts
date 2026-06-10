import type { SiteContext } from "@/types/site";

import type { StructuralRecommendations } from "@/types/site";

import { surroundingsLabel } from "@/lib/site-surroundings";



export const PROPOSAL_DISCLAIMER =

  "This is a preliminary model-generation proposal only. " +

  "It is not a code-compliant structural design. " +

  "Final member sizes, wind loads, connections and foundations must be verified by a licensed structural engineer.";

export const PROPOSAL_DISCLAIMER_SHORT =
  "Starting model only — verify with a structural engineer before construction.";



export function terrainLabelLong(terrain: string): string {

  const labels: Record<string, string> = {

    "0": "Coastal / open (Cat 0)",

    II: "Open terrain (Cat II)",

    III: "Suburban (Cat III)",

    IV: "Urban (Cat IV)",

  };

  return labels[terrain] ?? terrain;

}



export function formatClimateLine(site: SiteContext): string {

  return (

    `Climate estimate: mean wind ~${site.mean_wind_ms.toFixed(1)} m/s, ` +

    `exposure proxy ${site.design_wind_proxy_ms.toFixed(1)} m/s. ` +

    `Code wind speed was not calculated.`

  );

}



/** Primary terrain line for proposals — shows final selected context only. */

export function formatSiteTerrainLine(site: SiteContext): string {

  const applied = site.surroundings_applied ?? "auto";

  const terrainLabel =

    applied === "auto"

      ? `Terrain: ${terrainLabelLong(site.terrain_class)}`

      : `Selected terrain: ${terrainLabelLong(site.terrain_class)}`;

  return `${terrainLabel} · load index ${site.load_index.toFixed(1)}`;

}



/** Optional lineage when user override changed terrain from map detection. */

export function formatSiteOverrideNote(site: SiteContext): string | null {

  const applied = site.surroundings_applied ?? "auto";

  if (applied === "auto") return null;

  if (

    site.detected_terrain_class == null ||

    site.detected_load_index == null ||

    (site.detected_terrain_class === site.terrain_class &&

      Math.abs(site.detected_load_index - site.load_index) < 0.05)

  ) {

    return `User surroundings: ${surroundingsLabel(applied)}.`;

  }

  return (

    `Initial map detection: ${terrainLabelLong(site.detected_terrain_class)} · ` +

    `load index ${site.detected_load_index.toFixed(1)} · ` +

    `${surroundingsLabel(applied)} override applied.`

  );

}



export function formatSiteSummary(site: SiteContext): string {

  const overrideNote = formatSiteOverrideNote(site);

  const lines = [

    `Site data for ${site.location_label || "your location"}:`,

    `• ${formatClimateLine(site)}`,

    `• ${formatSiteTerrainLine(site)}`,

  ];

  if (overrideNote) {

    lines.push(`• ${overrideNote}`);

  }

  return lines.join("\n");

}



export function formatSuggestedConfiguration(rec: StructuralRecommendations): string {

  const bays = (rec.bay_spacing_mm / 1000).toFixed(2).replace(/\.?0+$/, "");

  const frameType = rec.use_truss

    ? `${rec.truss_type.toUpperCase()} truss`

    : "portal frames";

  return `Suggested configuration: ${frameType}, ${rec.column_profile} columns, ~${bays} m bays.`;

}



export function formatStartingSections(

  rec: StructuralRecommendations,

  bracingProfile = "L50x50",

): string {

  const lines = [`Columns: ${rec.column_profile}`];

  if (rec.use_truss && rec.truss_chord_profile) {

    lines.push(`Truss chords: ${rec.truss_chord_profile}`);

  }

  if (rec.use_truss && rec.truss_web_profile) {

    lines.push(`Truss webs: ${rec.truss_web_profile}`);

  }

  lines.push(`Bracing: ${bracingProfile}`);

  return lines.map((l) => `  - ${l}`).join("\n");

}



export function formatBracingEnabled(rec: StructuralRecommendations): string {

  const parts: string[] = [];

  if (rec.x_bracing) parts.push("wall X-bracing");

  if (rec.roof_bracing) parts.push("roof X-bracing");

  if (rec.gable_bracing) parts.push("gable X-bracing");

  if (rec.sag_rods) parts.push("anti-sag rods");

  if (parts.length === 0) return "Bracing: none suggested.";

  return `Bracing enabled: ${parts.join(", ")}.`;

}


