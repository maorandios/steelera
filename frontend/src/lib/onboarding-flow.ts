import type { ChatMessage, QuickRepliesPayload } from "@/types/chat";
import { formatSiteSummary } from "@/lib/proposal-copy";
import type { SiteContext } from "@/types/site";
import type { WizardStep1Data, WizardStep2Data } from "@/types/wizard";

export { formatSiteSummary } from "@/lib/proposal-copy";

export type OnboardingPhase =
  | "location"
  | "site_refine"
  | "use_case"
  | "width"
  | "length"
  | "height"
  | "roof_style"
  | "roof_pitch"
  | "proposal";

export const CUSTOM_VALUE = "__custom__";

export const DIMENSION_PRESETS_MM = {
  width: [12_000, 15_000, 18_000, 24_000],
  length: [20_000, 30_000, 40_000, 50_000],
  height: [5_000, 6_000, 7_000, 8_000],
} as const;

function formatM(mm: number): string {
  return mm % 1000 === 0 ? `${mm / 1000} m` : `${(mm / 1000).toFixed(1)} m`;
}

function quickReplies(
  phase: OnboardingPhase,
  payload: Omit<QuickRepliesPayload, "onboardingPhase">,
): NonNullable<ChatMessage["ui_block"]> {
  return { type: "quick_replies", payload: { onboardingPhase: phase, ...payload } };
}

export function initialOnboardingMessage(): ChatMessage {
  return {
    role: "assistant",
    content: "",
    ui_block: { type: "location_picker", payload: {} },
  };
}

export function isOnboardingStartScreen(state: {
  onboardingPhase: OnboardingPhase;
  onboardingAwaitingCustom: OnboardingPhase | null;
  isProposing: boolean;
  messages: ChatMessage[];
}): boolean {
  return (
    state.onboardingPhase === "location" &&
    !state.onboardingAwaitingCustom &&
    !state.isProposing &&
    state.messages.length === 1 &&
    state.messages[0].role === "assistant" &&
    state.messages[0].ui_block?.type === "location_picker"
  );
}

export function stripInitialOnboardingWelcome(
  messages: ChatMessage[],
): ChatMessage[] {
  if (
    messages.length === 1 &&
    messages[0].role === "assistant" &&
    messages[0].ui_block?.type === "location_picker"
  ) {
    return [];
  }
  return messages;
}

export function siteConfirmedMessage(site: SiteContext): ChatMessage {
  return {
    role: "assistant",
    content:
      `${formatSiteSummary(site)}\n\n` +
      `Initial map detection — does this match your plot? City lookups often land on the urban center; adjust if your site is on open or industrial land.`,
    ui_block: { type: "site_refine", payload: {} },
  };
}

export function useCaseMessage(): ChatMessage {
  return {
    role: "assistant",
    content: "What will this structure be used for?",
    ui_block: quickReplies("use_case", {
      options: [
        { label: "Warehouse", value: "Industrial warehouse" },
        { label: "Workshop", value: "Workshop" },
        { label: "Storage", value: "Storage shed" },
        { label: "Farm building", value: "Farm building" },
        { label: "Other…", value: CUSTOM_VALUE },
      ],
    }),
  };
}

export function messagesAfterSiteSurroundingsConfirm(
  site: SiteContext,
  step1: WizardStep1Data,
  priorMessages: ChatMessage[],
  userLabel: string,
): { messages: ChatMessage[]; phase: OnboardingPhase } {
  const base: ChatMessage[] = [
    ...priorMessages,
    { role: "user", content: userLabel },
    {
      role: "assistant",
      content: `${formatSiteSummary(site)}\n\nAdjusted for your site surroundings.`,
    },
  ];

  if (step1.use_case.trim()) {
    return {
      phase: "width",
      messages: [...base, nextOnboardingMessage("width", step1, {})],
    };
  }

  return {
    phase: "use_case",
    messages: [...base, useCaseMessage()],
  };
}

export function mapPinMessage(lat: number, lon: number): ChatMessage {
  return {
    role: "assistant",
    content: "Tap the map to place the pin on your exact site, then confirm.",
    ui_block: { type: "map_pin_picker", payload: { latitude: lat, longitude: lon } },
  };
}

export function nextOnboardingMessage(
  phase: OnboardingPhase,
  step1: WizardStep1Data,
  _step2: Partial<WizardStep2Data>,
): ChatMessage {
  switch (phase) {
    case "width":
      return {
        role: "assistant",
        content: `Great — ${step1.use_case}.\n\nHow wide should the building be?`,
        ui_block: quickReplies("width", {
          options: DIMENSION_PRESETS_MM.width.map((mm) => ({
            label: formatM(mm),
            value: String(mm),
          })),
          allowCustom: true,
          customPlaceholder: "e.g. 16",
          customUnit: "m",
        }),
      };
    case "length":
      return {
        role: "assistant",
        content: `${formatM(step1.width_mm)} wide — noted.\n\nHow long?`,
        ui_block: quickReplies("length", {
          options: DIMENSION_PRESETS_MM.length.map((mm) => ({
            label: formatM(mm),
            value: String(mm),
          })),
          allowCustom: true,
          customPlaceholder: "e.g. 35",
          customUnit: "m",
        }),
      };
    case "height":
      return {
        role: "assistant",
        content: `Footprint ${formatM(step1.width_mm)} × ${formatM(step1.length_mm)}.\n\nWhat eave height do you need?`,
        ui_block: quickReplies("height", {
          options: DIMENSION_PRESETS_MM.height.map((mm) => ({
            label: formatM(mm),
            value: String(mm),
          })),
          allowCustom: true,
          customPlaceholder: "e.g. 6.5",
          customUnit: "m",
        }),
      };
    case "roof_style":
      return {
        role: "assistant",
        content: `${formatM(step1.height_mm)} eave height — good clearance.\n\nWhich roof line do you prefer?`,
        ui_block: quickReplies("roof_style", {
          options: [
            { label: "Duo-pitch", value: "duo_pitch" },
            { label: "Mono-pitch", value: "mono_pitch" },
            { label: "Flat", value: "flat" },
          ],
        }),
      };
    case "roof_pitch":
      return {
        role: "assistant",
        content: "What roof pitch works for you?",
        ui_block: quickReplies("roof_pitch", {
          options: [
            { label: "5°", value: "5" },
            { label: "10°", value: "10" },
            { label: "15°", value: "15" },
            { label: "20°", value: "20" },
          ],
        }),
      };
    default:
      return initialOnboardingMessage();
  }
}

export function parseMetresInput(text: string): number | null {
  const t = text.trim().replace(/,/g, "").toLowerCase();
  const match = t.match(/^([\d.]+)\s*(?:m|metres?|meters?)?$/);
  if (!match) return null;
  const metres = parseFloat(match[1]);
  if (!Number.isFinite(metres) || metres <= 0) return null;
  return Math.round(metres * 1000);
}

export function roofStyleLabel(style: string): string {
  return style.replace(/_/g, " ");
}

export function userLabelForPhase(
  phase: OnboardingPhase,
  value: string,
  step1: WizardStep1Data,
  step2: Partial<WizardStep2Data>,
): string {
  switch (phase) {
    case "location":
      return step1.location_label || value;
    case "use_case":
      return value;
    case "width":
      return `${formatM(Number(value))} wide`;
    case "length":
      return `${formatM(Number(value))} long`;
    case "height":
      return `${formatM(Number(value))} eave height`;
    case "roof_style":
      return roofStyleLabel(value);
    case "roof_pitch":
      return `${value}° pitch`;
    case "proposal":
      return "Build structure";
    default:
      return value;
  }
}

export function nextPhaseAfter(
  current: OnboardingPhase,
  step2: Partial<WizardStep2Data>,
): OnboardingPhase {
  switch (current) {
    case "location":
      return "site_refine";
    case "site_refine":
      return "use_case";
    case "use_case":
      return "width";
    case "width":
      return "length";
    case "length":
      return "height";
    case "height":
      return "roof_style";
    case "roof_style":
      return step2.roof_style === "flat" ? "proposal" : "roof_pitch";
    case "roof_pitch":
      return "proposal";
    default:
      return "proposal";
  }
}
