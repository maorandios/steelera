"use client";

import { create } from "zustand";

import {
  fetchSiteContext,
  geocodeLocation,
  postChat,
  postGenerateShed,
  postProposeShed,
  type GenerateShedBody,
} from "@/lib/api";
import { gridDefinitionToLayout } from "@/lib/grid-proposal";
import {
  extractGridIntentFromMessages,
} from "@/lib/grid-intent";
import { gridLayoutToShedParams, isStructuralGridLayout } from "@/lib/grid-layout";
import { extractProfilesFromMessages } from "@/lib/profile-overrides";
import {
  DEFAULT_SHED_PARAMS,
  inferShedParamsFromElements,
  mergeShedParams,
  SHED_ASSEMBLY_ID,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import {
  assemblyParamsToShedConfig,
  shedConfigToAssemblyParams,
} from "@/lib/shed-config";
import type { ShedAssemblyConfig } from "@/types/shed-config";
import type { StructuralGridLayout } from "@/types/spatial-grid";
import {
  buildStructuralGridState,
  DEFAULT_STRUCTURAL_GRID,
  structuralGridFromShedParams,
  type StructuralGridState,
} from "@/lib/structural-grid";
import { checklistPayloadToShedParams } from "@/lib/shed-checklist";
import {
  CUSTOM_VALUE,
  initialOnboardingMessage,
  messagesAfterSiteSurroundingsConfirm,
  nextOnboardingMessage,
  nextPhaseAfter,
  parseMetresInput,
  mapPinMessage,
  siteConfirmedMessage,
  stripInitialOnboardingWelcome,
  userLabelForPhase,
  type OnboardingPhase,
} from "@/lib/onboarding-flow";
import {
  SITE_BUILT_UP,
  SITE_OPEN_INDUSTRIAL,
  SITE_PIN,
  surroundingsLabel,
  type SiteSurroundings,
} from "@/lib/site-surroundings";
import type { SiteContext } from "@/types/site";
import type { StructuralTopology } from "@/types/ifc-topology";
import type {
  ChatMessage,
  ShedChecklistPayload,
  ShedChecklistSelections,
} from "@/types/chat";
import type { GridDefinition } from "@/types/spatial-grid";
import type {
  ShedProposalResult,
  UiPhase,
  WizardStep1Data,
  WizardStep2Data,
} from "@/types/wizard";
import type {
  ElementAlignment,
  ElementRotation,
  ProjectElementMm,
} from "@/types/project";
import { emptyProjectState, normalizeElement } from "@/types/project";

/** Keep API payloads bounded so long chats stay responsive. */
const API_MESSAGE_WINDOW = 24;

const DEFAULT_WIZARD_STEP2: WizardStep2Data = {
  roof_style: "duo_pitch",
  roof_pitch_deg: 10,
  exposure: "open",
  bay_spacing_mm: 6_000,
};

async function fetchAndShowProposal(
  step1: WizardStep1Data,
  step2: WizardStep2Data,
  priorMessages: ChatMessage[],
): Promise<{
  proposal: ShedProposalResult;
  messages: ChatMessage[];
}> {
  const result = await postProposeShed({
    use_case: step1.use_case,
    width_mm: step1.width_mm,
    length_mm: step1.length_mm,
    height_mm: step1.height_mm,
    roof_style: step2.roof_style,
    roof_pitch_deg: step2.roof_pitch_deg,
    latitude: step1.latitude,
    longitude: step1.longitude,
    location_label: step1.location_label,
    site_surroundings: step1.site_surroundings,
    bay_spacing_mm: step2.bay_spacing_mm,
  });
  return {
    proposal: result,
    messages: [
      ...priorMessages,
      {
        role: "assistant",
        content: `Your starting model for ${result.summary}.\n\nRecommended sections are pre-selected — pick Light or Conservative if you prefer, then Build model.`,
        ui_block: { type: "show_proposal" as const, payload: {} },
      },
    ],
  };
}

function projectElementsFingerprint(elements: ProjectElementMm[]): string {
  return elements
    .map(
      (element) =>
        `${element.id}:${element.position_mm.x},${element.position_mm.y},${element.position_mm.z}:${element.length_mm}`,
    )
    .join("|");
}

function isStructuralChatRequest(text: string): boolean {
  const t = text.toLowerCase();
  if (/\b(duplicate|copy|array|multiply|clone|delete)\b/.test(t)) return false;
  return (
    /\b(build|create|design|generate|make|shed|portal|frame|warehouse|structure|truss|church|hall)\b/.test(
      t,
    ) ||
    /\d+\s*[x×]\s*\d+/.test(t) ||
    /\d+\s*(?:m|mm)\b/.test(t)
  );
}

function applyElementsFromApi(
  incoming: ProjectElementMm[],
  existing: ProjectElementMm[],
): ProjectElementMm[] {
  return incoming.map((element) => {
    const prior = existing.find((item) => item.id === element.id);
    return normalizeElement({
      ...element,
      rotation: prior?.rotation ?? element.rotation,
      alignment: prior?.alignment ?? element.alignment,
      rotation_euler_deg:
        element.rotation_euler_deg ?? prior?.rotation_euler_deg ?? null,
    });
  });
}

const DEFAULT_WIZARD_STEP1: WizardStep1Data = {
  use_case: "",
  width_mm: 15_000,
  length_mm: 30_000,
  height_mm: 6_000,
  latitude: null,
  longitude: null,
  location_label: "",
  site_surroundings: "auto",
};

interface ProjectStore {
  uiPhase: UiPhase;
  onboardingPhase: OnboardingPhase;
  onboardingAwaitingCustom: OnboardingPhase | null;
  wizardStep1: WizardStep1Data;
  wizardStep2: WizardStep2Data;
  siteContext: SiteContext | null;
  proposal: ShedProposalResult | null;
  proposalDraft: GridDefinition | null;
  isProposing: boolean;
  messages: ChatMessage[];
  projectElements: ProjectElementMm[];
  shedAssemblyParams: ShedAssemblyParams | null;
  structuralGrid: StructuralGridState;
  selectedElementId: string | null;
  structuralTopology: StructuralTopology | null;
  statuses: string[];
  isLoading: boolean;
  isMacroLoading: boolean;
  error: string | null;
  answerOnboarding: (value: string) => Promise<void>;
  submitOnboardingCustom: (text: string) => Promise<void>;
  setOnboardingLocation: (
    lat: number,
    lon: number,
    label: string,
  ) => Promise<void>;
  confirmSiteRefine: (choice: string) => Promise<void>;
  confirmSiteMapPin: (lat: number, lon: number) => Promise<void>;
  requestLocationCustom: () => void;
  updateWizardStep1: (patch: Partial<WizardStep1Data>) => void;
  setOnboardingPhase: (phase: OnboardingPhase | "start") => void;
  updateProposalDraft: (patch: Partial<GridDefinition>) => void;
  applyProposalTier: (tier: import("@/types/wizard").SectionTierName) => void;
  buildFromProposal: () => Promise<void>;
  completeTransition: () => void;
  sendMessage: (content: string) => Promise<void>;
  confirmShedChecklist: (
    payload: ShedChecklistPayload,
    selections: ShedChecklistSelections,
  ) => Promise<void>;
  generateShedMacro: (body: GenerateShedBody) => Promise<void>;
  modifyShedAssembly: (partial: Partial<ShedAssemblyParams>) => Promise<void>;
  setProjectElements: (elements: ProjectElementMm[]) => void;
  setStructuralGridFromSpans: (xSpacingInput: string, zSpacingInput: string) => void;
  clearError: () => void;
  selectElement: (id: string) => void;
  selectAssembly: (assemblyId: string, focusElementId?: string | null) => void;
  clearSelection: () => void;
  updateElementRotation: (id: string, rotation: ElementRotation) => void;
  updateElementAlignment: (id: string, alignment: ElementAlignment) => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  uiPhase: "onboarding",
  onboardingPhase: "location",
  onboardingAwaitingCustom: null,
  wizardStep1: { ...DEFAULT_WIZARD_STEP1 },
  wizardStep2: { ...DEFAULT_WIZARD_STEP2 },
  siteContext: null,
  proposal: null,
  proposalDraft: null,
  isProposing: false,
  messages: [initialOnboardingMessage()],
  projectElements: emptyProjectState().projectElements,
  shedAssemblyParams: null,
  structuralGrid: { ...DEFAULT_STRUCTURAL_GRID },
  selectedElementId: null,
  structuralTopology: null,
  statuses: [],
  isLoading: false,
  isMacroLoading: false,
  error: null,

  setOnboardingLocation: async (lat, lon, label) => {
    if (get().uiPhase !== "onboarding" || get().isProposing) return;
    set({ statuses: ["Fetching site wind and terrain data…"], error: null });
    try {
      const site = await fetchSiteContext(lat, lon, label);
      const step1 = {
        ...get().wizardStep1,
        latitude: lat,
        longitude: lon,
        location_label: label,
      };
      const prior = stripInitialOnboardingWelcome(get().messages);
      const nextMessages: ChatMessage[] = [
        ...prior,
        { role: "user", content: label },
        siteConfirmedMessage(site),
      ];
      set({
        wizardStep1: step1,
        siteContext: site,
        onboardingPhase: "site_refine",
        onboardingAwaitingCustom: null,
        statuses: [],
        error: null,
        messages: nextMessages,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load site data";
      set({ statuses: [], error: message });
    }
  },

  confirmSiteRefine: async (choice) => {
    if (get().uiPhase !== "onboarding" || get().onboardingPhase !== "site_refine") {
      return;
    }
    const step1 = get().wizardStep1;
    if (step1.latitude === null || step1.longitude === null) return;

    if (choice === SITE_PIN) {
      set({
        messages: [
          ...get().messages,
          { role: "user", content: "Pin exact site on map" },
          mapPinMessage(step1.latitude, step1.longitude),
        ],
        error: null,
      });
      return;
    }

    if (choice === SITE_BUILT_UP) {
      const userLabel = surroundingsLabel(SITE_BUILT_UP);
      const priorMessages = get().messages;
      set({
        statuses: ["Applying built-up / urban exposure…"],
        error: null,
        messages: [...priorMessages, { role: "user", content: userLabel }],
      });

      try {
        const site = await fetchSiteContext(
          step1.latitude,
          step1.longitude,
          step1.location_label,
          SITE_BUILT_UP,
        );
        const step1BuiltUp: WizardStep1Data = {
          ...step1,
          site_surroundings: SITE_BUILT_UP,
        };
        const { messages, phase } = messagesAfterSiteSurroundingsConfirm(
          site,
          step1BuiltUp,
          priorMessages,
          userLabel,
        );
        set({
          wizardStep1: step1BuiltUp,
          siteContext: site,
          onboardingPhase: phase,
          statuses: [],
          messages,
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update site data";
        set({ statuses: [], error: message });
      }
      return;
    }

    if (choice !== SITE_OPEN_INDUSTRIAL) return;

    const userLabel = surroundingsLabel(SITE_OPEN_INDUSTRIAL);
    const priorMessages = get().messages;
    set({
      statuses: ["Applying open-site exposure…"],
      error: null,
      messages: [...priorMessages, { role: "user", content: userLabel }],
    });

    try {
      const site = await fetchSiteContext(
        step1.latitude,
        step1.longitude,
        step1.location_label,
        SITE_OPEN_INDUSTRIAL,
      );
      const step1Open: WizardStep1Data = {
        ...step1,
        site_surroundings: SITE_OPEN_INDUSTRIAL,
      };
      const { messages, phase } = messagesAfterSiteSurroundingsConfirm(
        site,
        step1Open,
        priorMessages,
        userLabel,
      );
      set({
        wizardStep1: step1Open,
        siteContext: site,
        onboardingPhase: phase,
        statuses: [],
        messages,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to update site data";
      set({ statuses: [], error: message });
    }
  },

  confirmSiteMapPin: async (lat, lon) => {
    if (get().uiPhase !== "onboarding" || get().onboardingPhase !== "site_refine") {
      return;
    }
    const step1 = get().wizardStep1;
    const label = step1.location_label
      ? `${step1.location_label} (pinned)`
      : "Pinned site";

    set({ statuses: ["Fetching site data for pinned location…"], error: null });
    try {
      const site = await fetchSiteContext(lat, lon, label, "auto");
      const nextStep1 = {
        ...step1,
        latitude: lat,
        longitude: lon,
        location_label: label,
      };
      set({
        wizardStep1: { ...nextStep1, site_surroundings: "auto" },
        siteContext: site,
        statuses: [],
        error: null,
        messages: [
          ...get().messages,
          {
            role: "user",
            content: `Pinned at ${lat.toFixed(4)}, ${lon.toFixed(4)}`,
          },
          siteConfirmedMessage(site),
        ],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load pinned site";
      set({ statuses: [], error: message });
    }
  },

  requestLocationCustom: () => {
    set({ onboardingAwaitingCustom: "location", error: null });
  },

  updateWizardStep1: (patch) => {
    set({ wizardStep1: { ...get().wizardStep1, ...patch } });
  },

  setOnboardingPhase: (phase) => {
    if (get().uiPhase !== "onboarding" || get().isProposing) return;
    if (phase === "start") {
      set({
        onboardingPhase: "location",
        onboardingAwaitingCustom: null,
        messages: [initialOnboardingMessage()],
        error: null,
      });
      return;
    }
    set({ onboardingPhase: phase, onboardingAwaitingCustom: null, error: null });
  },

  answerOnboarding: async (value) => {
    if (get().uiPhase !== "onboarding" || get().isProposing) return;
    const phase = get().onboardingPhase;
    if (phase === "proposal") return;

    if (value === CUSTOM_VALUE) {
      set({ onboardingAwaitingCustom: phase, error: null });
      return;
    }

    await get().submitOnboardingCustom(value);
  },

  submitOnboardingCustom: async (rawValue) => {
    if (get().uiPhase !== "onboarding" || get().isProposing) return;

    const phase = get().onboardingAwaitingCustom ?? get().onboardingPhase;
    if (phase === "proposal") return;

    const trimmed = rawValue.trim();
    if (!trimmed) return;

    let value = trimmed;
    if (phase === "width" || phase === "length" || phase === "height") {
      if (/^\d+$/.test(trimmed) && Number(trimmed) >= 1000) {
        value = trimmed;
      } else {
        const mm = parseMetresInput(trimmed);
        if (mm === null || mm < 1000) {
          set({ error: "Enter a valid dimension in metres (e.g. 15)." });
          return;
        }
        value = String(mm);
      }
    } else if (phase === "location") {
      set({ statuses: ["Looking up address…"], error: null });
      try {
        const geo = await geocodeLocation(trimmed);
        await get().setOnboardingLocation(
          geo.latitude,
          geo.longitude,
          geo.display_name || trimmed,
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Could not find that location";
        set({ statuses: [], error: message });
      }
      return;
    } else if (phase === "use_case") {
      value = trimmed;
    }

    const step1 = { ...get().wizardStep1 };
    const step2 = { ...get().wizardStep2 };

    switch (phase) {
      case "use_case":
        step1.use_case = value;
        break;
      case "width":
        step1.width_mm = Number(value);
        break;
      case "length":
        step1.length_mm = Number(value);
        break;
      case "height":
        step1.height_mm = Number(value);
        break;
      case "roof_style":
        step2.roof_style = value as WizardStep2Data["roof_style"];
        if (value === "flat") step2.roof_pitch_deg = 0;
        break;
      case "roof_pitch":
        step2.roof_pitch_deg = Number(value);
        break;
      default:
        return;
    }

    const userContent = userLabelForPhase(phase, value, step1, step2);
    const nextMessages: ChatMessage[] = [
      ...get().messages,
      { role: "user", content: userContent },
    ];
    const nextPhase = nextPhaseAfter(phase, step2);

    set({
      wizardStep1: step1,
      wizardStep2: step2,
      onboardingPhase: nextPhase,
      onboardingAwaitingCustom: null,
      error: null,
      messages: nextMessages,
    });

    if (nextPhase === "proposal") {
      set({
        isProposing: true,
        statuses: ["Computing proposal and running AI review…"],
        messages: [
          ...nextMessages,
          {
            role: "assistant",
            content: "Let me work out the best structural layout for your site…",
          },
        ],
      });
      try {
        const { proposal, messages } = await fetchAndShowProposal(
          step1,
          step2,
          nextMessages,
        );
        set({
          proposal,
          proposalDraft: { ...proposal.grid_definition },
          isProposing: false,
          statuses: [],
          messages,
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to compute proposal";
        set({
          isProposing: false,
          statuses: [],
          onboardingPhase: step2.roof_style === "flat" ? "roof_style" : "roof_pitch",
          error: message,
          messages: [
            ...nextMessages,
            {
              role: "assistant",
              content: `Sorry, I couldn't compute the proposal: ${message}\n\nCheck the backend on port 8000 and try again.`,
              ui_block: nextOnboardingMessage(
                step2.roof_style === "flat" ? "roof_style" : "roof_pitch",
                step1,
                step2,
              ).ui_block,
            },
          ],
        });
      }
      return;
    }

    const assistantMessage = nextOnboardingMessage(nextPhase, step1, step2);
    set({ messages: [...nextMessages, assistantMessage] });
  },

  updateProposalDraft: (patch) => {
    const draft = get().proposalDraft;
    if (!draft) return;
    set({ proposalDraft: { ...draft, ...patch } });
  },

  applyProposalTier: (tier) => {
    const proposal = get().proposal;
    const draft = get().proposalDraft;
    if (!proposal?.section_tiers?.length || !draft) return;
    const pkg = proposal.section_tiers.find((t) => t.tier === tier);
    if (!pkg) return;
    set({
      proposalDraft: {
        ...draft,
        column_profile: pkg.column_profile,
        bracing_profile: pkg.bracing_profile,
        truss_chord_profile: pkg.truss_chord_profile ?? draft.truss_chord_profile,
        truss_web_profile: pkg.truss_web_profile ?? draft.truss_web_profile,
        tie_beam_profile: pkg.tie_beam_profile ?? draft.tie_beam_profile,
      },
    });
  },

  buildFromProposal: async () => {
    const draft = get().proposalDraft;
    if (!draft) {
      throw new Error("No proposal to build");
    }
    set({
      uiPhase: "transition",
      statuses: ["Generating structural model…"],
      messages: [
        ...get().messages,
        {
          role: "assistant",
          content:
            "Building your structure now — the 3D model will appear momentarily.",
        },
      ],
    });
    try {
      await get().generateShedMacro(gridDefinitionToLayout(draft));
    } catch {
      set({ uiPhase: "onboarding", onboardingPhase: "proposal", statuses: [] });
      throw new Error("Build failed — check the backend on port 8000.");
    }
  },

  completeTransition: () => {
    set({
      uiPhase: "workspace",
      statuses: [],
      messages: [
        ...get().messages,
        {
          role: "assistant",
          content:
            "Your structure is ready in the workspace. Select members in the viewport, refine in the side panels, or ask me to modify the design.",
        },
      ],
    });
  },

  setProjectElements: (elements) =>
    set({
      projectElements: elements.map((element) => normalizeElement(element)),
      selectedElementId: null,
    }),

  setStructuralGridFromSpans: (xSpacingInput, zSpacingInput) =>
    set({
      structuralGrid: buildStructuralGridState(xSpacingInput, zSpacingInput),
    }),

  clearError: () => set({ error: null }),

  confirmShedChecklist: async (payload, selections) => {
    const params = checklistPayloadToShedParams(payload, selections);
    const config = assemblyParamsToShedConfig(params);
    await get().generateShedMacro(config);
    set((state) => ({
      messages: [
        ...state.messages,
        {
          role: "assistant",
          content:
            "Awesome! I've calculated the structural system and generated the blueprint with your selected configurations on the 3D canvas.",
        },
      ],
    }));
  },

  generateShedMacro: async (body: GenerateShedBody) => {
    // Chat keeps isLoading true while awaiting macro; only block concurrent macros.
    if (get().isMacroLoading) return;

    const selectedId = get().selectedElementId;
    const isGridLayout = isStructuralGridLayout(body);
    const fromBody = isGridLayout
      ? gridLayoutToShedParams(body as StructuralGridLayout)
      : shedConfigToAssemblyParams(body as ShedAssemblyConfig);
    const chatProfiles = extractProfilesFromMessages(get().messages);
    const chatIntent = extractGridIntentFromMessages(get().messages);
    const profileOverrides = {
      column_profile: chatProfiles.column_profile,
      bracing_profile: chatProfiles.bracing_profile,
      purlin_profile: chatProfiles.purlin_profile,
      girt_profile: chatProfiles.girt_profile,
      sag_rod_profile: chatProfiles.sag_rod_profile,
      base_plate_profile: chatProfiles.base_plate_profile,
      truss_chord_profile: chatProfiles.truss_chord_profile,
      truss_web_profile: chatProfiles.truss_web_profile,
    };
    const params = mergeShedParams(
      mergeShedParams(get().shedAssemblyParams ?? DEFAULT_SHED_PARAMS, fromBody),
      isGridLayout
        ? profileOverrides
        : {
            ...profileOverrides,
            use_truss: chatIntent.use_truss ?? fromBody.use_truss,
            truss_type: chatIntent.truss_type ?? fromBody.truss_type,
            roof_style: chatIntent.roof_style ?? fromBody.roof_style,
            roof_pitch_deg: chatIntent.roof_pitch_deg ?? fromBody.roof_pitch_deg,
            use_bracing: chatIntent.x_bracing ?? fromBody.use_bracing,
            use_gable_bracing:
              chatIntent.gable_bracing ?? fromBody.use_gable_bracing,
            use_roof_bracing: chatIntent.roof_bracing ?? fromBody.use_roof_bracing,
            use_sag_rods: chatIntent.sag_rods ?? fromBody.use_sag_rods,
            use_haunches: chatIntent.haunches ?? fromBody.use_haunches,
            use_fly_braces: chatIntent.fly_braces ?? fromBody.use_fly_braces,
            use_base_plates: chatIntent.base_plates ?? fromBody.use_base_plates,
            use_bottom_chord_restraint:
              chatIntent.bottom_chord_restraint ?? fromBody.use_bottom_chord_restraint,
            generate_wall_girts:
              chatIntent.generate_wall_girts ?? fromBody.generate_wall_girts,
            generate_tie_beams:
              chatIntent.generate_tie_beams ?? fromBody.generate_tie_beams,
          },
    );

    set({ isMacroLoading: true, error: null });

    try {
      let apiPayload: GenerateShedBody;
      if (isGridLayout) {
        const layout = body as StructuralGridLayout;
        // AI/backend grid_definition is authoritative — only overlay profile picks.
        const gd = layout.grid_definition;
        apiPayload = {
          ...layout,
          replace_existing: layout.replace_existing ?? true,
          structural_members: [],
          grid_definition: {
            ...gd,
            column_profile: profileOverrides.column_profile ?? gd.column_profile,
            bracing_profile:
              profileOverrides.bracing_profile ?? gd.bracing_profile,
            purlin_profile: profileOverrides.purlin_profile ?? gd.purlin_profile,
            girt_profile: profileOverrides.girt_profile ?? gd.girt_profile,
            sag_rod_profile:
              profileOverrides.sag_rod_profile ?? gd.sag_rod_profile,
            base_plate_profile:
              profileOverrides.base_plate_profile ?? gd.base_plate_profile,
            truss_chord_profile:
              profileOverrides.truss_chord_profile ?? gd.truss_chord_profile,
            truss_web_profile:
              profileOverrides.truss_web_profile ?? gd.truss_web_profile,
          },
        };
      } else {
        apiPayload = assemblyParamsToShedConfig(
          params,
          body.assembly_id ?? SHED_ASSEMBLY_ID,
        );
        apiPayload.replace_existing = body.replace_existing ?? true;
      }
      const response = await postGenerateShed(apiPayload);
      const elements = (response.projectElements ?? []).map((element) =>
        normalizeElement(element),
      );
      const fromElements = inferShedParamsFromElements(elements);
      // User/grid/checklist params must win over geometry inference (infer defaults
      // to duo_pitch and would undo mono-pitch truss on the next sidebar regen).
      const finalParams = fromElements
        ? mergeShedParams(fromElements, params)
        : params;
      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );
      const topology = response.structural_topology ?? null;
      set({
        projectElements: elements,
        shedAssemblyParams: finalParams,
        structuralGrid: structuralGridFromShedParams(finalParams),
        structuralTopology: topology,
        isMacroLoading: false,
        selectedElementId: selectedStillExists ? selectedId : null,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to generate shed macro";
      set({ isMacroLoading: false, error: message });
      throw err;
    }
  },

  modifyShedAssembly: async (partial) => {
    const current =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!current) {
      throw new Error("No shed assembly in the project. Generate a shed first.");
    }
    await get().generateShedMacro(
      assemblyParamsToShedConfig(mergeShedParams(current, partial)),
    );
  },

  selectElement: (id) => set({ selectedElementId: id }),

  selectAssembly: (assemblyId, focusElementId = null) => {
    const { structuralTopology, projectElements } = get();
    const fromTopology =
      structuralTopology?.assemblies[assemblyId]?.entity_ids ?? [];
    const fromElements = projectElements
      .filter((e) => e.primary_assembly_id === assemblyId)
      .map((e) => e.id);
    const ids = fromTopology.length > 0 ? fromTopology : fromElements;
    const focus =
      focusElementId && ids.includes(focusElementId)
        ? focusElementId
        : ids[0] ?? null;
    set({ selectedElementId: focus });
  },

  clearSelection: () => set({ selectedElementId: null }),

  updateElementRotation: (id, rotation) =>
    set((state) => ({
      projectElements: state.projectElements.map((element) =>
        element.id === id ? { ...element, rotation } : element,
      ),
    })),

  updateElementAlignment: (id, alignment) =>
    set((state) => ({
      projectElements: state.projectElements.map((element) =>
        element.id === id ? { ...element, alignment } : element,
      ),
    })),

  sendMessage: async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || get().isLoading) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...get().messages, userMessage];
    const projectState = {
      version: 3 as const,
      projectElements: get().projectElements,
    };

    set({
      messages: nextMessages,
      isLoading: true,
      statuses: ["Sending..."],
      error: null,
    });

    try {
      const selectedId = get().selectedElementId;
      const apiMessages = nextMessages.slice(-API_MESSAGE_WINDOW);
      const response = await postChat(
        apiMessages,
        projectState,
        selectedId,
      );
      const priorElements = get().projectElements;
      const incoming =
        response.projectElements ??
        response.projectState?.projectElements ??
        [];
      const gridLayoutRaw =
        response.structural_grid_layout ??
        response.shed_assembly_config;
      let elements = priorElements;
      let nextShedParams = get().shedAssemblyParams;

      if (gridLayoutRaw && get().uiPhase === "workspace") {
        set({ statuses: ["Resolving structural members on spatial grid..."] });
        await get().generateShedMacro(
          gridLayoutRaw as StructuralGridLayout | ShedAssemblyConfig,
        );
        elements = get().projectElements;
        nextShedParams = get().shedAssemblyParams;
        if (elements.length === 0) {
          throw new Error(
            "Shed macro returned no elements. Check the backend on port 8000.",
          );
        }
      } else if (incoming.length > 0 && !isStructuralChatRequest(trimmed)) {
        elements = applyElementsFromApi(incoming, priorElements);
        const inferredShed = elements.some(
          (element) => element.assembly_id === SHED_ASSEMBLY_ID,
        )
          ? inferShedParamsFromElements(elements)
          : null;
        nextShedParams = inferredShed ?? get().shedAssemblyParams;
      }

      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.message.content,
        ui_block: response.message.ui_block ?? null,
      };

      set({
        messages: [...nextMessages, assistantMessage],
        projectElements: elements,
        shedAssemblyParams: nextShedParams,
        structuralGrid: nextShedParams
          ? structuralGridFromShedParams(nextShedParams)
          : get().structuralGrid,
        statuses: [],
        isLoading: false,
        selectedElementId: selectedStillExists ? selectedId : null,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to reach Steelera API";
      set({
        isLoading: false,
        statuses: [],
        error: message,
        messages: [
          ...nextMessages,
          {
            role: "assistant",
            content: `Sorry, something went wrong: ${message}. Is the backend running on port 8000?`,
          },
        ],
      });
    }
  },
}));

export function useSelectedElement(): ProjectElementMm | null {
  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const projectElements = useProjectStore((state) => state.projectElements);
  if (!selectedElementId) return null;
  return projectElements.find((element) => element.id === selectedElementId) ?? null;
}

export function useIsElementHighlighted(elementId: string): boolean {
  const selected = useProjectStore((state) => state.selectedElementId);
  return selected === elementId;
}
