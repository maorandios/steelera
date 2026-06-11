import {
  DIMENSION_PRESETS_MM,
  roofStyleLabel,
  type OnboardingPhase,
} from "@/lib/onboarding-flow";
import type { WizardStep1Data, WizardStep2Data } from "@/types/wizard";

export type WizardStepDef = {
  phase: OnboardingPhase;
  label: string;
};

const PHASE_ORDER: OnboardingPhase[] = [
  "site_refine",
  "use_case",
  "width",
  "length",
  "height",
  "roof_style",
  "roof_pitch",
  "proposal",
];

export function formatMm(mm: number): string {
  return mm % 1000 === 0 ? `${mm / 1000} m` : `${(mm / 1000).toFixed(1)} m`;
}

export function buildWizardSteps(
  step2: WizardStep2Data,
  currentPhase: OnboardingPhase,
): WizardStepDef[] {
  const steps: WizardStepDef[] = [
    { phase: "site_refine", label: "Site" },
    { phase: "use_case", label: "Structure" },
    { phase: "width", label: "Width" },
    { phase: "length", label: "Length" },
    { phase: "height", label: "Height" },
    { phase: "roof_style", label: "Roof" },
  ];

  const needsPitch =
    step2.roof_style === "duo_pitch" ||
    step2.roof_style === "mono_pitch" ||
    currentPhase === "roof_pitch";

  if (needsPitch) {
    steps.push({ phase: "roof_pitch", label: "Pitch" });
  }

  steps.push({ phase: "proposal", label: "Model" });
  return steps;
}

export function phaseIndex(
  phase: OnboardingPhase,
  steps: WizardStepDef[],
): number {
  return steps.findIndex((s) => s.phase === phase);
}

export function previousPhase(
  current: OnboardingPhase,
  steps: WizardStepDef[],
): OnboardingPhase | "start" {
  const idx = phaseIndex(current, steps);
  if (idx <= 0) return "start";
  return steps[idx - 1].phase;
}

export function stepSummary(
  phase: OnboardingPhase,
  step1: WizardStep1Data,
  step2: WizardStep2Data,
): string | null {
  switch (phase) {
    case "site_refine":
      return step1.location_label || null;
    case "use_case":
      return step1.use_case || null;
    case "width":
      return step1.width_mm ? formatMm(step1.width_mm) : null;
    case "length":
      return step1.length_mm ? formatMm(step1.length_mm) : null;
    case "height":
      return step1.height_mm ? formatMm(step1.height_mm) : null;
    case "roof_style":
      return step2.roof_style ? roofStyleLabel(step2.roof_style) : null;
    case "roof_pitch":
      return step2.roof_pitch_deg ? `${step2.roof_pitch_deg}°` : null;
    default:
      return null;
  }
}

export function stepContent(phase: OnboardingPhase, step1: WizardStep1Data) {
  switch (phase) {
    case "site_refine":
      return {
        title: "Confirm your site",
        description:
          "We pulled wind and terrain data from open maps. Does this match your plot?",
      };
    case "use_case":
      return {
        title: "What are you building?",
        description: "Pick a structure type to size the preliminary frame.",
      };
    case "width":
      return {
        title: "Building width",
        description: step1.use_case
          ? `How wide should your ${step1.use_case.toLowerCase()} be?`
          : "How wide should the building be?",
      };
    case "length":
      return {
        title: "Building length",
        description: `${formatMm(step1.width_mm)} wide — how long along the ridge?`,
      };
    case "height":
      return {
        title: "Eave height",
        description: `Footprint ${formatMm(step1.width_mm)} × ${formatMm(step1.length_mm)} — clear height at the eaves?`,
      };
    case "roof_style":
      return {
        title: "Roof type",
        description: `${formatMm(step1.height_mm)} eave height — which roof line works best?`,
      };
    case "roof_pitch":
      return {
        title: "Roof pitch",
        description: "Choose a pitch angle for drainage and headroom.",
      };
    case "proposal":
      return {
        title: "Your preliminary model",
        description: "Review the layout, pick a steel package, then build.",
      };
    default:
      return { title: "", description: "" };
  }
}

export const USE_CASE_OPTIONS = [
  { label: "Portal shed", value: "Portal shed" },
  { label: "Warehouse", value: "Industrial warehouse" },
  { label: "Workshop", value: "Workshop" },
  { label: "Mezzanine", value: "Mezzanine" },
  { label: "Storage shed", value: "Storage shed" },
  { label: "Pipe rack", value: "Pipe rack" },
  { label: "Farm building", value: "Farm building" },
  { label: "Stairs", value: "Stairs" },
] as const;

export const ROOF_STYLE_OPTIONS = [
  { label: "Duo-pitch", value: "duo_pitch" },
  { label: "Mono-pitch", value: "mono_pitch" },
  { label: "Flat", value: "flat" },
] as const;

export const ROOF_PITCH_OPTIONS = ["5", "10", "15", "20"] as const;

export function dimensionPresets(phase: "width" | "length" | "height") {
  return DIMENSION_PRESETS_MM[phase].map((mm) => ({
    label: formatMm(mm),
    value: String(mm),
  }));
}

export { PHASE_ORDER };
