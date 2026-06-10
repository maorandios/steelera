import type { GridDefinition } from "@/types/spatial-grid";
import type { SectionTierName, SectionTierPackage } from "@/types/wizard";

/** Match backend COLUMN_UTIL_MEANINGFUL_MIN — util below is floor-dominated. */
export const COLUMN_UTIL_MEANINGFUL_MIN = 0.45;

export const CHORD_UTIL_MEANINGFUL_MIN = 0.15;

/** Match backend TIE_UTIL_MEANINGFUL_MIN. */
export const TIE_UTIL_MEANINGFUL_MIN = 0.15;

const TIER_LABELS: Record<SectionTierName, string> = {
  light: "Light",
  recommended: "Recommended",
  conservative: "Conservative",
};

export function tierLabel(tier: SectionTierName): string {
  return TIER_LABELS[tier];
}

export function activeTierFromDraft(
  tiers: SectionTierPackage[],
  draft: GridDefinition,
): SectionTierName | null {
  const match = tiers.find(
    (t) =>
      t.column_profile === draft.column_profile &&
      (t.bracing_profile || "L50x50") === (draft.bracing_profile || "L50x50") &&
      (t.truss_chord_profile ?? null) === (draft.truss_chord_profile ?? null) &&
      (t.truss_web_profile ?? null) === (draft.truss_web_profile ?? null) &&
      (t.tie_beam_profile ?? "IPE200") === (draft.tie_beam_profile ?? "IPE200"),
  );
  return match?.tier ?? null;
}

export function fmtUtil(u: number | null | undefined): string {
  if (u == null) return "—";
  return u.toFixed(2);
}

export function fmtColumnUtil(u: number | null | undefined): string {
  if (u == null || u < COLUMN_UTIL_MEANINGFUL_MIN) return "—";
  return u.toFixed(2);
}

export function fmtChordUtil(u: number | null | undefined): string {
  if (u == null || u < CHORD_UTIL_MEANINGFUL_MIN) return "—";
  return u.toFixed(2);
}

export function fmtTieUtil(u: number | null | undefined): string {
  if (u == null || u < TIE_UTIL_MEANINGFUL_MIN) return "—";
  return u.toFixed(2);
}

export function hasLowColumnUtilWarning(warnings: string[] | undefined): boolean {
  if (!warnings?.length) return false;
  return warnings.some(
    (w) =>
      w.toLowerCase().includes("column utilization") ||
      w.toLowerCase().includes("column util") ||
      w.toLowerCase().includes("low utilization"),
  );
}

export function hasLowChordUtilWarning(warnings: string[] | undefined): boolean {
  if (!warnings?.length) return false;
  return warnings.some(
    (w) =>
      w.toLowerCase().includes("chord utilization") ||
      w.toLowerCase().includes("chord util"),
  );
}

export function hasMinimumRulesSummary(warnings: string[] | undefined): boolean {
  if (!warnings?.length) return false;
  return warnings.some((w) =>
    w.toLowerCase().includes("minimum geometry/stability rules"),
  );
}
