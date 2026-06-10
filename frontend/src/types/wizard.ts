import type { GridDefinition } from "@/types/spatial-grid";
import type { ShedRoofStyle } from "@/types/macro";
import type { SiteSurroundings } from "@/lib/site-surroundings";
import type { SiteContext, StructuralRecommendations } from "@/types/site";

export type UiPhase = "onboarding" | "transition" | "workspace";

export type WizardStep = 1 | 2 | 3;

export type SiteExposure = "open" | "sheltered";

export interface WizardStep1Data {
  use_case: string;
  width_mm: number;
  length_mm: number;
  height_mm: number;
  latitude: number | null;
  longitude: number | null;
  location_label: string;
  site_surroundings: SiteSurroundings;
}

export interface WizardStep2Data {
  roof_style: ShedRoofStyle;
  roof_pitch_deg: number;
  exposure: SiteExposure;
  bay_spacing_mm: number | null;
}

export type SectionTierName = "light" | "recommended" | "conservative";

export interface SectionTierPackage {
  tier: SectionTierName;
  column_profile: string;
  column_utilization?: number | null;
  truss_chord_profile?: string | null;
  chord_utilization?: number | null;
  truss_web_profile?: string | null;
  web_utilization?: number | null;
  tie_beam_profile?: string;
  tie_beam_utilization?: number | null;
  bracing_profile: string;
  bracing_utilization?: number | null;
}

export interface AiProposalReview {
  narrative: string;
  recommended_tier: SectionTierName;
  comparison_summary: string;
  concerns: string[];
  ai_available: boolean;
}

export interface ShedProposalResult {
  grid_definition: GridDefinition;
  rationale: string[];
  summary: string;
  site_context?: SiteContext | null;
  recommendations?: StructuralRecommendations | null;
  section_tiers?: SectionTierPackage[];
  warnings?: string[];
  ai_review?: AiProposalReview | null;
  active_tier?: SectionTierName;
}

export interface ShedProposalRequest {
  use_case?: string;
  width_mm: number;
  length_mm: number;
  height_mm: number;
  roof_style: ShedRoofStyle;
  roof_pitch_deg: number;
  latitude?: number | null;
  longitude?: number | null;
  location_label?: string;
  site_surroundings?: SiteSurroundings;
  exposure?: SiteExposure | null;
  bay_spacing_mm?: number | null;
}
