import type { GridDefinition } from "@/types/spatial-grid";
import type { ShedRoofStyle } from "@/types/macro";

export type UiPhase = "onboarding" | "transition" | "workspace";

export type WizardStep = 1 | 2 | 3;

export type SiteExposure = "open" | "sheltered";

export interface WizardStep1Data {
  use_case: string;
  width_mm: number;
  length_mm: number;
  height_mm: number;
}

export interface WizardStep2Data {
  roof_style: ShedRoofStyle;
  roof_pitch_deg: number;
  exposure: SiteExposure;
  bay_spacing_mm: number | null;
}

export interface ShedProposalResult {
  grid_definition: GridDefinition;
  rationale: string[];
  summary: string;
}

export interface ShedProposalRequest {
  use_case?: string;
  width_mm: number;
  length_mm: number;
  height_mm: number;
  roof_style: ShedRoofStyle;
  roof_pitch_deg: number;
  exposure: SiteExposure;
  bay_spacing_mm?: number | null;
}
