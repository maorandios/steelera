"use client";

import { create } from "zustand";

import {
  geocodeLocation,
  fetchGroundPlacementNodes,
  fetchSnapNodes,
  postChat,
  postDeleteMembers,
  postGenerateShed,
  postPlaceBraceLeg,
  postPlaceBracingCross,
  postPlaceGridColumn,
  postPlaceGridTieBeam,
  postPlaceMemberBetweenPoints,
  postPlaceWallXBrace,
  postPlaceXBraceFromLeg,
  postProposeShed,
  postUpdateProfile,
  fetchSketchAnalysis,
  type GenerateShedBody,
} from "@/lib/api";
import {
  applyTrussTypeGlobally,
  applyTrussTypeToFrame,
  insertBayIndexForFrame,
  insertFrameAfter,
  removeFrameAt,
  switchFrameToRafter,
  switchFrameToTruss,
} from "@/lib/assembly-edit";
import {
  extractPendingProfileFromMessages,
  WORKSPACE_PICK_ON_MODEL,
} from "@/lib/pending-profile";
import {
  resolveColumnTargetIds,
  type ColumnEditScope,
  isColumnElement,
} from "@/lib/column-member-scope";
import { resolveSelectionContext } from "@/lib/selection-context";
import { selectionContextToPayload } from "@/lib/selection-context-payload";
import {
  assemblyIdFromElements,
  gridPlacementFromStructuralGrid,
  inferTrussedZLabels,
  resolveBaySelection,
  shedParamsToGridPlacement,
  zLabelsForGrid,
} from "@/lib/grid-selection";
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
import { placeholderSiteContext } from "@/lib/placeholder-site";
import { applySiteSurroundingsOverride } from "@/lib/site-override";
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
import type {
  PickedNode,
  PlacementIntent,
  ProfileScope,
  SelectionContext,
  SnapNode,
  ViewportMode,
} from "@/types/interaction";
import {
  dedupePlacements,
  findMatchingBracingPlacements,
  findMatchingRoofXBraceLegs,
  findMatchingTieBeamSegments,
  isTrussRoofBracing,
} from "@/lib/sketch-bay-match";
import { buildFallbackSketchAnalysis } from "@/lib/sketch-advise-fallback";
import {
  inferWallXBraceCorners,
  resolveXBraceCorners,
  verifyXBraceLegsInModel,
} from "@/lib/brace-corners";
import {
  buildSketchSnapNodes,
  findSketchNodeById,
  isSketchableElement,
} from "@/lib/sketch-nodes";
import { SKETCH_GHOST_FACE_OPACITY } from "@/lib/sketch-viewport";
import {
  intentLabel,
  normalizeProfile,
  recognizeStructuralIntent,
  recommendProfiles,
} from "@/lib/structural-intent";
import type {
  AddBracingScope,
  AddElementKind,
  AddElementSession,
  BracingPanel,
  PickablePanel,
  TieBeamLocation,
  TieBeamPanel,
} from "@/types/add-element";
import type {
  ColumnPickMode,
  GridSelectionContext,
  GroundPlacementNode,
} from "@/types/grid-selection";
import { resolveTieBeamPlacement } from "@/lib/tie-panel-placement";
import { defaultBracingProfile, defaultTieBeamProfile } from "@/lib/wall-panel";
import type {
  EnrichedSnapNode,
  SketchApplyScope,
  SketchSession,
  StructuralIntentKind,
} from "@/types/sketch";
import type { TrussType } from "@/types/shed-config";
import type { OperationProposal, StructuralOperationKind } from "@/types/structural-advise";
import { emptyProjectState, normalizeElement } from "@/types/project";

function emptySketchSession(): SketchSession {
  return {
    phase: "idle",
    firstNodeId: null,
    lockedLine: null,
    intent: null,
    intentOverride: null,
    analysis: null,
    analysisLoading: false,
    selectedOperationId: null,
    dialogueStep: 1,
    selectedProfile: null,
    applyScope: null,
  };
}

async function loadSketchAnalysis(
  get: () => ProjectStore,
  set: (partial: Partial<ProjectStore> | ((state: ProjectStore) => Partial<ProjectStore>)) => void,
  locked: { start: EnrichedSnapNode; end: EnrichedSnapNode },
  intentOverride?: StructuralIntentKind | null,
) {
  try {
    const analysis = await fetchSketchAnalysis({
      projectElements: get().projectElements,
      startNode: locked.start,
      endNode: locked.end,
      intentOverride: intentOverride ?? null,
      siteContext: get().siteContext,
      shedParams: get().shedAssemblyParams as Record<string, unknown> | null,
      xCoordsMm: get().structuralGrid.xCoordsMm,
      zCoordsMm: get().structuralGrid.zCoordsMm,
    });
    if (!analysis.operations?.length) {
      const fallback = buildFallbackSketchAnalysis(
        locked.start,
        locked.end,
        get().projectElements,
      );
      return {
        analysis: {
          ...fallback,
          ...analysis,
          operations: fallback.operations,
          recommended_operation_id:
            analysis.recommended_operation_id ?? fallback.recommended_operation_id,
          summary: analysis.summary ?? analysis.message ?? fallback.summary,
        },
        intent: analysis.intent,
      };
    }
    return { analysis, intent: analysis.intent };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Structural advise unavailable";
    const fallback = buildFallbackSketchAnalysis(
      locked.start,
      locked.end,
      get().projectElements,
    );
    set({
      statuses: [
        `Using offline advice (${message}). Start backend on port 8000 for full analysis.`,
      ],
    });
    return { analysis: fallback, intent: fallback.intent };
  }
}

/** Keep API payloads bounded so long chats stay responsive. */
const API_MESSAGE_WINDOW = 24;

function trussTypeHint(
  params: ShedAssemblyParams | null,
): string | null {
  if (!params?.use_truss) return null;
  return params.truss_type;
}

function refreshSelectionContext(
  elementId: string | null,
  elements: ProjectElementMm[],
  params: ShedAssemblyParams | null,
): SelectionContext | null {
  if (!elementId) return null;
  const element = elements.find((e) => e.id === elementId);
  if (!element) return null;
  return resolveSelectionContext(element, elements, {
    trussType: trussTypeHint(params),
  });
}

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
  if (/\b(switch to|apply)\s+(hea|heb|ipe|rhs|shs)\b/.test(t)) return false;
  if (/^(hea|heb|ipe|rhs|shs)\d/i.test(t.trim())) return false;
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
  if (incoming.length === 0) {
    return existing;
  }

  const priorById = new Map(existing.map((element) => [element.id, element]));
  const normalizeFromApi = (element: ProjectElementMm): ProjectElementMm => {
    const prior = priorById.get(element.id);
    return normalizeElement({
      ...element,
      rotation: prior?.rotation ?? element.rotation,
      alignment: prior?.alignment ?? element.alignment,
      rotation_euler_deg:
        element.rotation_euler_deg ?? prior?.rotation_euler_deg ?? null,
    });
  };

  const dedupeById = (elements: ProjectElementMm[]) =>
    elements.filter((element, index, array) => {
      const first = array.findIndex((item) => item.id === element.id);
      return first === index;
    });

  if (incoming.length >= existing.length) {
    return dedupeById(incoming.map(normalizeFromApi));
  }

  const merged = new Map(existing.map((element) => [element.id, element]));
  for (const element of incoming) {
    merged.set(element.id, normalizeFromApi(element));
  }
  return Array.from(merged.values());
}

function resolveSketchOperationKind(
  op: OperationProposal | undefined,
  selectedOperationId: string | null,
): StructuralOperationKind {
  if (op?.kind) return op.kind;
  const id = op?.id ?? selectedOperationId;
  if (id === "full_x") return "place_x_brace";
  if (id === "multi_panel_x") return "place_multi_panel_x";
  if (id === "single_leg") return "place_single_member";
  return "place_single_member";
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

export type MemberPickIntent = "profile" | "rotation" | "alignment" | "delete";

export type MemberPickMode = {
  intent: MemberPickIntent;
  profile?: string;
  rotation?: ElementRotation;
  alignment?: ElementAlignment;
  updatedCount: number;
  /** Delete pick: columns staged for batch removal. */
  pickedIds?: string[];
};

export type MemberPickStart =
  | { intent: "profile"; profile: string }
  | { intent: "rotation"; rotation: ElementRotation }
  | { intent: "alignment"; alignment: ElementAlignment }
  | { intent: "delete" };

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
  selectionContext: SelectionContext | null;
  gridSelectionContext: GridSelectionContext | null;
  groundPlacementNodes: GroundPlacementNode[];
  columnPickMode: ColumnPickMode | null;
  viewportMode: ViewportMode;
  placementIntent: PlacementIntent | null;
  placementProfile: string | null;
  pickedNodes: PickedNode[];
  snapNodes: SnapNode[];
  structuralTopology: StructuralTopology | null;
  statuses: string[];
  isLoading: boolean;
  isMacroLoading: boolean;
  error: string | null;
  memberPickMode: MemberPickMode | null;
  sketchSession: SketchSession;
  sketchSnapNodes: EnrichedSnapNode[];
  addElementSession: AddElementSession | null;
  hoveredWallPanel: PickablePanel | null;
  startAddElement: () => void;
  /** @deprecated use startAddElement */
  startAddBracing: () => void;
  selectAddElementKind: (kind: AddElementKind) => void;
  cancelAddElement: () => void;
  selectWallPanel: (panel: PickablePanel) => void;
  setHoveredWallPanel: (panel: PickablePanel | null) => void;
  setAddBracingProfile: (profile: string) => void;
  setAddTieBeamProfile: (profile: string) => void;
  commitAddTieBeam: (location: TieBeamLocation) => Promise<void>;
  setAddBracingBraceCount: (count: number) => void;
  commitAddBracing: (scope: AddBracingScope) => Promise<void>;
  startSketchMode: () => void;
  cancelSketchMode: () => void;
  pickSketchNode: (node: EnrichedSnapNode) => Promise<void>;
  selectSketchOperation: (operationId: string) => void;
  confirmSketchIntent: () => void;
  setSketchIntentOverride: (kind: StructuralIntentKind) => Promise<void>;
  selectSketchProfile: (profile: string) => void;
  setSketchApplyScope: (scope: SketchApplyScope) => void;
  commitSketchElement: (scopeOverride?: SketchApplyScope) => Promise<void>;
  startMemberPickMode: (start: MemberPickStart) => void;
  applyMemberPick: (elementId: string) => Promise<void>;
  commitDeleteMemberPick: () => Promise<void>;
  finishMemberPickMode: () => void;
  cancelMemberPickMode: () => void;
  /** @deprecated use startMemberPickMode */
  startProfilePickMode: (profile: string) => void;
  applyColumnProfile: (
    profile: string,
    scope: ColumnEditScope,
  ) => Promise<void>;
  applyColumnRotation: (
    rotation: ElementRotation,
    scope: ColumnEditScope,
  ) => Promise<void>;
  applyColumnAlignment: (
    alignment: ElementAlignment,
    scope: ColumnEditScope,
  ) => Promise<void>;
  deleteColumnsScoped: (scope: ColumnEditScope) => Promise<void>;
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
  selectGridBay: (bayIndex: number) => void;
  selectAssembly: (assemblyId: string, focusElementId?: string | null) => void;
  clearSelection: () => void;
  placeGridColumn: (
    xAxis: string,
    zAxis: string,
    profile?: string,
  ) => Promise<void>;
  placeGridTieBeam: (
    xAxis: string,
    profile?: string,
    elevation?: string,
  ) => Promise<void>;
  startColumnPickMode: (options?: {
    profile?: string;
    tieProfile?: string;
    addTieInBay?: boolean;
    extraWallOffsetsMm?: number[];
  }) => Promise<void>;
  pickGroundPlacementNode: (node: GroundPlacementNode) => Promise<void>;
  cancelColumnPickMode: () => void;
  startNodePlacement: (
    intent: Exclude<PlacementIntent, "insert_frame">,
    options?: { profile?: string },
  ) => Promise<void>;
  cancelNodePlacement: () => void;
  pickSnapNode: (node: SnapNode) => Promise<void>;
  updateMemberProfile: (profile: string, scope: ProfileScope) => Promise<void>;
  deleteSelectedMembers: (scope: "selection" | "pair" | "group") => Promise<void>;
  changeTrussType: (
    trussType: Exclude<TrussType, "none">,
    scope?: "frame" | "all",
  ) => Promise<void>;
  switchFramePrimary: (mode: "truss" | "rafter") => Promise<void>;
  startFramePlacement: () => void;
  pickGridFrameLine: (frameIndex: number) => Promise<void>;
  cancelGridPlacement: () => void;
  removeSelectedFrame: () => Promise<void>;
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
  selectionContext: null,
  gridSelectionContext: null,
  groundPlacementNodes: [],
  columnPickMode: null,
  viewportMode: "inspect",
  placementIntent: null,
  placementProfile: null,
  pickedNodes: [],
  snapNodes: [],
  structuralTopology: null,
  statuses: [],
  isLoading: false,
  isMacroLoading: false,
  error: null,
  memberPickMode: null,
  sketchSession: emptySketchSession(),
  sketchSnapNodes: [],
  addElementSession: null,
  hoveredWallPanel: null,

  startAddElement: () => {
    const elements = get().projectElements;
    if (elements.length === 0) {
      set({ error: "Generate a structure before adding elements." });
      return;
    }
    set({
      viewportMode: "inspect",
      addElementSession: { step: "choose_kind" },
      hoveredWallPanel: null,
      selectedElementId: null,
      selectionContext: null,
      gridSelectionContext: null,
      placementIntent: null,
      pickedNodes: [],
      error: null,
      statuses: ["Choose what to add — bracing or tie beam."],
    });
  },

  startAddBracing: () => {
    get().startAddElement();
  },

  selectAddElementKind: (kind) => {
    const session = get().addElementSession;
    if (!session || session.step !== "choose_kind") return;
    const elements = get().projectElements;
    const profile =
      kind === "bracing"
        ? defaultBracingProfile(elements)
        : defaultTieBeamProfile(elements);
    set({
      viewportMode: "pick_panel",
      addElementSession:
        kind === "bracing"
          ? {
              type: "bracing",
              step: "pick_panel",
              panel: null,
              profile,
              braceCount: 1,
            }
          : {
              type: "tie_beam",
              step: "pick_panel",
              panel: null,
              profile,
              location: null,
            },
      hoveredWallPanel: null,
      statuses: [
        kind === "bracing"
          ? "Click a wall, gable, or roof panel in the viewport."
          : "Click a wall, gable, or truss panel in the viewport.",
      ],
    });
  },

  cancelAddElement: () =>
    set({
      viewportMode: "inspect",
      addElementSession: null,
      hoveredWallPanel: null,
      statuses: [],
    }),

  selectWallPanel: (panel) => {
    const session = get().addElementSession;
    if (!session || !("type" in session) || session.step !== "pick_panel") {
      return;
    }
    if (session.type === "bracing") {
      if (
        panel.kind !== "long_wall" &&
        panel.kind !== "gable_wall" &&
        panel.kind !== "roof"
      ) {
        return;
      }
      set({
        addElementSession: {
          ...session,
          panel: panel as BracingPanel,
          step: "profile",
        },
        viewportMode: "inspect",
        hoveredWallPanel: null,
        statuses: [],
      });
      return;
    }
    if (panel.kind === "roof") return;
    set({
      addElementSession: {
        ...session,
        panel: panel as TieBeamPanel,
        step: "profile",
      },
      viewportMode: "inspect",
      hoveredWallPanel: null,
      statuses: [],
    });
  },

  setHoveredWallPanel: (panel) => set({ hoveredWallPanel: panel }),

  setAddBracingProfile: (profile) => {
    const session = get().addElementSession;
    if (!session || !("type" in session) || session.type !== "bracing") return;
    set({
      addElementSession: {
        ...session,
        profile: profile.trim().toUpperCase(),
        step: "brace_count",
      },
    });
  },

  setAddBracingBraceCount: (count) => {
    const session = get().addElementSession;
    if (!session || !("type" in session) || session.type !== "bracing") return;
    const braceCount = Math.min(5, Math.max(1, Math.round(count)));
    set({
      addElementSession: {
        ...session,
        braceCount,
        step: "scope",
      },
    });
  },

  setAddTieBeamProfile: (profile) => {
    const session = get().addElementSession;
    if (!session || !("type" in session) || session.type !== "tie_beam") return;
    set({
      addElementSession: {
        ...session,
        profile: profile.trim().toUpperCase(),
        step: "location",
      },
    });
  },

  commitAddTieBeam: async (location: TieBeamLocation) => {
    const session = get().addElementSession;
    if (
      !session ||
      !("type" in session) ||
      session.type !== "tie_beam" ||
      !session.panel
    ) {
      return;
    }
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before placing tie beams." });
      return;
    }
    const panel = session.panel;
    const profile = session.profile.trim().toUpperCase();
    if (!profile) return;

    const placement = resolveTieBeamPlacement(
      panel,
      location,
      get().structuralGrid,
    );
    const gridCtx = gridPlacementFromStructuralGrid(
      get().structuralGrid,
      params,
    );
    const body: Parameters<typeof postPlaceGridTieBeam>[1] = {
      orientation: placement.orientation,
      x_axis: placement.x_axis,
      z_start: placement.z_start,
      z_end: placement.z_end,
      z_axis: placement.z_axis,
      x_start: placement.x_start,
      x_end: placement.x_end,
      profile,
      elevation: placement.elevation,
      placement_label: location,
      grid: gridCtx,
      assembly_id: assemblyIdFromElements(get().projectElements),
    };

    set({ isLoading: true, error: null, statuses: ["Placing tie beam…"] });
    try {
      const result = await postPlaceGridTieBeam(
        get().projectElements,
        body,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        isLoading: false,
        viewportMode: "inspect",
        addElementSession: null,
        hoveredWallPanel: null,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place tie beam";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  commitAddBracing: async (scope) => {
    const session = get().addElementSession;
    if (
      !session ||
      !("type" in session) ||
      session.type !== "bracing" ||
      !session.panel
    ) {
      return;
    }
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before placing bracing." });
      return;
    }
    set({ isLoading: true, error: null, statuses: ["Placing X-bracing…"] });
    try {
      const panel = session.panel;
      const panelKind =
        panel.kind === "gable_wall"
          ? "gable_wall"
          : panel.kind === "roof"
            ? "roof"
            : "long_wall";
      const result = await postPlaceWallXBrace(get().projectElements, {
        panel_kind: panelKind,
        wall_x:
          panel.kind === "gable_wall"
            ? panel.xStart
            : panel.kind === "roof"
              ? panel.xStart
              : panel.wallXLabel,
        bay_index:
          panel.kind === "long_wall"
            ? panel.bayIndex
            : panel.kind === "roof"
              ? panel.bayIndex
              : 0,
        frame_z: panel.kind === "gable_wall" ? panel.frameZ : null,
        x_start:
          panel.kind === "gable_wall" || panel.kind === "roof"
            ? panel.xStart
            : null,
        x_end:
          panel.kind === "gable_wall" || panel.kind === "roof"
            ? panel.xEnd
            : null,
        z_start:
          panel.kind === "long_wall" || panel.kind === "roof"
            ? panel.zStart
            : null,
        z_end:
          panel.kind === "long_wall" || panel.kind === "roof"
            ? panel.zEnd
            : null,
        elev_start: panel.kind === "roof" ? panel.elevStart : null,
        elev_end: panel.kind === "roof" ? panel.elevEnd : null,
        slope_side: panel.kind === "roof" ? panel.slopeSide : null,
        brace_count: session.braceCount,
        profile: session.profile,
        scope,
        grid: shedParamsToGridPlacement(params),
        assembly_id: assemblyIdFromElements(get().projectElements),
      });
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        isLoading: false,
        viewportMode: "inspect",
        addElementSession: null,
        hoveredWallPanel: null,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place wall bracing";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  startSketchMode: () => {
    const elements = get().projectElements;
    if (elements.length === 0) {
      set({ error: "Generate a structure before sketching elements." });
      return;
    }
    const nodes = buildSketchSnapNodes(elements, get().structuralGrid);
    if (nodes.length < 2) {
      set({ error: "Not enough connection points to sketch." });
      return;
    }
    set({
      viewportMode: "sketch",
      sketchSession: emptySketchSession(),
      sketchSnapNodes: nodes,
      selectedElementId: null,
      selectionContext: null,
      gridSelectionContext: null,
      placementIntent: null,
      pickedNodes: [],
      error: null,
      statuses: [
        "Sketch mode — click two blue snap nodes to define a line.",
      ],
    });
  },

  cancelSketchMode: () =>
    set({
      viewportMode: "inspect",
      sketchSession: emptySketchSession(),
      sketchSnapNodes: [],
      statuses: [],
    }),

  pickSketchNode: async (node) => {
    if (get().viewportMode !== "sketch") return;
    const session = get().sketchSession;
    if (session.phase === "dialogue") return;

    const firstId = session.firstNodeId;
    if (!firstId) {
      set({
        sketchSession: {
          ...emptySketchSession(),
          phase: "picking",
          firstNodeId: node.id,
        },
        statuses: ["First node selected — click the second node."],
      });
      return;
    }

    const start = findSketchNodeById(get().sketchSnapNodes, firstId);
    if (!start) {
      set({ sketchSession: emptySketchSession() });
      return;
    }

    if (node.id === firstId) {
      set({
        sketchSession: emptySketchSession(),
        statuses: [
          "Sketch mode — click two blue snap nodes to define a line.",
        ],
      });
      return;
    }

    const locked = { start, end: node };
    set({
      sketchSession: {
        ...emptySketchSession(),
        phase: "dialogue",
        lockedLine: locked,
        analysisLoading: true,
        dialogueStep: 1,
      },
      statuses: ["Analyzing sketch…"],
    });

    const { analysis, intent } = await loadSketchAnalysis(get, set, locked);
    const recOp =
      analysis?.recommended_operation_id ??
      analysis?.operations?.[0]?.id ??
      null;
    set({
      sketchSession: {
        ...get().sketchSession,
        intent: analysis?.intent ?? intent,
        analysis,
        analysisLoading: false,
        selectedOperationId: recOp,
        dialogueStep: 1,
        selectedProfile:
          analysis?.profiles?.[0]?.profile ??
          analysis?.operations?.[0]?.profile_suggestions?.[0]?.profile ??
          null,
      },
      statuses: get().statuses.length ? get().statuses : [],
    });
  },

  selectSketchOperation: (operationId) => {
    const session = get().sketchSession;
    const op = session.analysis?.operations?.find((o) => o.id === operationId);
    const profiles =
      op?.profile_suggestions?.length
        ? op.profile_suggestions
        : session.analysis?.profiles ?? [];
    set({
      sketchSession: {
        ...session,
        selectedOperationId: operationId,
        dialogueStep: 2,
        selectedProfile: profiles[0]?.profile ?? session.selectedProfile,
      },
    });
  },

  confirmSketchIntent: () => {
    const session = get().sketchSession;
    const opId =
      session.selectedOperationId ??
      session.analysis?.recommended_operation_id ??
      session.analysis?.operations?.[0]?.id;
    if (opId) {
      get().selectSketchOperation(opId);
      return;
    }
    if (!session.intent && !session.intentOverride) return;
    const kind = session.intentOverride ?? session.intent?.kind ?? "unknown";
    const span = session.intent?.spanMm ?? 0;
    const profileOptions =
      session.analysis?.profiles ??
      recommendProfiles(span, kind).map((profile, i) => ({
        profile,
        tier: (i === 0 ? "recommended" : "light") as import("@/types/sketch").SketchProfileTier,
        tier_label: i === 0 ? "Optimal" : "Light",
        utilization: 0,
        governing: "span_rule",
      }));
    set({
      sketchSession: {
        ...session,
        dialogueStep: 2,
        selectedProfile: profileOptions[0]?.profile ?? null,
      },
    });
  },

  setSketchIntentOverride: async (kind) => {
    const session = get().sketchSession;
    const locked = session.lockedLine;
    if (!locked) return;

    set({
      sketchSession: {
        ...session,
        intentOverride: kind,
        dialogueStep: 1,
        analysisLoading: true,
      },
    });

    const { analysis } = await loadSketchAnalysis(get, set, locked, kind);
    const span = session.intent?.spanMm ?? 0;
    const fallbackProfile = recommendProfiles(span, kind)[0] ?? null;
    const recOp =
      analysis?.recommended_operation_id ??
      analysis?.operations?.[0]?.id ??
      null;
    set({
      sketchSession: {
        ...get().sketchSession,
        analysis: analysis ?? get().sketchSession.analysis,
        intentOverride: kind,
        dialogueStep: 1,
        analysisLoading: false,
        selectedOperationId: recOp,
        selectedProfile: analysis?.profiles[0]?.profile ?? fallbackProfile,
      },
    });
  },

  selectSketchProfile: (profile) => {
    const session = get().sketchSession;
    set({
      sketchSession: {
        ...session,
        selectedProfile: profile,
        dialogueStep: 3,
      },
    });
  },

  setSketchApplyScope: (scope) => {
    set({
      sketchSession: { ...get().sketchSession, applyScope: scope },
    });
  },

  commitSketchElement: async (scopeOverride) => {
    const session = get().sketchSession;
    const locked = session.lockedLine;
    const scope = scopeOverride ?? session.applyScope ?? "single";
    const op = session.analysis?.operations?.find(
      (o) => o.id === session.selectedOperationId,
    );
    const kind =
      (session.intentOverride ??
        session.intent?.kind ??
        op?.element_kind ??
        "unknown") as StructuralIntentKind;
    const profile = normalizeProfile(session.selectedProfile ?? "IPE200");
    if (!locked) return;

    const grid = get().structuralGrid;
    const assemblyId = assemblyIdFromElements(get().projectElements);
    const opKind = resolveSketchOperationKind(
      op,
      session.selectedOperationId,
    );

    set({ isLoading: true, error: null, statuses: ["Placing sketched element…"] });

    try {
      let elements = get().projectElements;
      const changedIds: string[] = [];
      const placedXLegIds: string[] = [];
      let statusNote = "";

      const template = {
        start: { x: locked.start.x, y: locked.start.y, z: locked.start.z },
        end: { x: locked.end.x, y: locked.end.y, z: locked.end.z },
      };

      const elementTypeForKind = ():
        | "bracing"
        | "tie_beam"
        | "purlin"
        | "beam" => {
        if (kind === "bracing") return "bracing";
        if (kind === "purlin") return "purlin";
        if (kind === "beam") return "beam";
        if (kind === "tie_beam") return "tie_beam";
        return "tie_beam";
      };

      if (opKind === "place_x_brace" || opKind === "place_multi_panel_x") {
        const roofX =
          op?.bracing_plane === "roof" ||
          isTrussRoofBracing(locked.start, locked.end);
        const legPlacements =
          scope === "single"
            ? [template]
            : roofX
              ? findMatchingRoofXBraceLegs(
                  elements,
                  template,
                  scope,
                  grid,
                  locked.start,
                  locked.end,
                )
              : findMatchingBracingPlacements(
                  elements,
                  template,
                  scope,
                  grid,
                  locked.start,
                  locked.end,
                );

        for (const p of dedupePlacements(legPlacements)) {
          const corners =
            scope === "single"
              ? resolveXBraceCorners(op, locked, elements)
              : inferWallXBraceCorners(
                  p.start,
                  p.end,
                  elements,
                  locked.start.elementId,
                  locked.end.elementId,
                );

          let result;
          if (corners) {
            result = await postPlaceBracingCross(
              elements,
              corners,
              profile,
              assemblyId,
            );
          } else {
            result = await postPlaceXBraceFromLeg(
              elements,
              p.start,
              p.end,
              {
                profile,
                assemblyId,
                startElementId: locked.start.elementId,
                endElementId: locked.end.elementId,
              },
            );
          }

          elements = applyElementsFromApi(result.projectElements, elements);
          changedIds.push(...result.changed_ids);

          if (opKind === "place_x_brace") {
            if (corners) {
              const verified = verifyXBraceLegsInModel(elements, corners);
              placedXLegIds.push(...verified.legIds);
              if (verified.legCount < 2) {
                throw new Error(
                  `Full X-brace incomplete — only ${verified.legCount} diagonal found in the model. Pick column snap nodes at opposite corners of the bay.`,
                );
              }
            } else {
              const newLegs = result.changed_ids.filter((id) =>
                id.includes("brace-custom"),
              );
              placedXLegIds.push(...newLegs);
              if (newLegs.length < 2) {
                throw new Error(
                  "Full X-brace incomplete — only one diagonal was placed. Pick column snap nodes on opposite corners of the bay.",
                );
              }
            }
          }
        }
        if (
          opKind === "place_multi_panel_x" &&
          op?.panel_count &&
          op.panel_count > 1
        ) {
          statusNote = ` Placed X in sketched panel; ${op.panel_count} panels recommended along slope — enable roof bracing in shed settings for full auto-layout.`;
        }
      } else {
        const placements =
          kind === "bracing"
            ? findMatchingBracingPlacements(
                elements,
                template,
                scope,
                grid,
                locked.start,
                locked.end,
              )
            : kind === "tie_beam" || kind === "beam"
              ? findMatchingTieBeamSegments(
                  template,
                  grid,
                  scope,
                  locked.start,
                  locked.end,
                )
              : [template];

        const placeType = elementTypeForKind();
        for (const p of dedupePlacements(placements)) {
          const result = await postPlaceMemberBetweenPoints(
            elements,
            p.start,
            p.end,
            {
              profile,
              assemblyId,
              elementType: placeType,
            },
          );
          elements = applyElementsFromApi(result.projectElements, elements);
          changedIds.push(...result.changed_ids);
        }
      }

      const label = op?.label ?? intentLabel(kind);
      const scopeLabel =
        scope === "all_bays"
          ? "all matching bays"
          : scope === "row"
            ? "this row"
            : "this location";
      const xLegIds =
        opKind === "place_x_brace"
          ? [...new Set(placedXLegIds)]
          : [];
      const memberNote =
        opKind === "place_x_brace" && xLegIds.length >= 2
          ? ` (${xLegIds.length} diagonals)`
          : "";

      set({
        projectElements: elements,
        viewportMode: "inspect",
        sketchSession: emptySketchSession(),
        sketchSnapNodes: [],
        isLoading: false,
        statuses: [],
        selectedElementId: xLegIds[0] ?? changedIds[0] ?? null,
        selectionContext: (() => {
          const id = xLegIds[0] ?? changedIds[0];
          if (!id) return null;
          const el = elements.find((e) => e.id === id);
          return el
            ? resolveSelectionContext(el, elements, {
                trussType: trussTypeHint(get().shedAssemblyParams),
              })
            : null;
        })(),
        messages: [
          ...get().messages,
          {
            role: "assistant",
            content: `Placed ${label} (${profile})${memberNote} across ${scopeLabel}.${statusNote}`,
          },
        ],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place sketched element";
      set({ isLoading: false, error: message, statuses: [] });
    }
  },

  startMemberPickMode: (start) => {
    const pickHint =
      start.intent === "delete"
        ? "Click columns in the viewport to pick them, then click Remove."
        : "Click columns in the viewport. Tap Done when finished.";
    const keepSelection = start.intent === "delete";
    set({
      viewportMode: "pick_members_profile",
      memberPickMode: {
        ...start,
        updatedCount: 0,
        pickedIds: start.intent === "delete" ? [] : undefined,
      },
      selectedElementId: keepSelection ? get().selectedElementId : null,
      selectionContext: keepSelection ? get().selectionContext : null,
      gridSelectionContext: null,
      placementIntent: null,
      pickedNodes: [],
      statuses: [pickHint],
    });
  },

  startProfilePickMode: (profile) => {
    get().startMemberPickMode({ intent: "profile", profile });
  },

  applyMemberPick: async (elementId) => {
    const pick = get().memberPickMode;
    if (!pick) return;
    const element = get().projectElements.find((e) => e.id === elementId);
    if (!element || !isColumnElement(element)) return;

    try {
      if (pick.intent === "profile" && pick.profile) {
        set({ statuses: [`Applying ${pick.profile}…`] });
        const result = await postUpdateProfile(
          get().projectElements,
          pick.profile,
          elementId,
          "selection",
        );
        const elements = applyElementsFromApi(
          result.projectElements,
          get().projectElements,
        );
        set({
          projectElements: elements,
          memberPickMode: {
            ...pick,
            updatedCount: pick.updatedCount + 1,
          },
          statuses: [],
          error: null,
        });
        return;
      }

      if (pick.intent === "rotation" && pick.rotation !== undefined) {
        set((state) => ({
          projectElements: state.projectElements.map((el) =>
            el.id === elementId ? { ...el, rotation: pick.rotation } : el,
          ),
          memberPickMode: {
            ...pick,
            updatedCount: pick.updatedCount + 1,
          },
          statuses: [],
        }));
        return;
      }

      if (pick.intent === "alignment" && pick.alignment) {
        set((state) => ({
          projectElements: state.projectElements.map((el) =>
            el.id === elementId ? { ...el, alignment: pick.alignment } : el,
          ),
          memberPickMode: {
            ...pick,
            updatedCount: pick.updatedCount + 1,
          },
          statuses: [],
        }));
        return;
      }

      if (pick.intent === "delete") {
        const picked = pick.pickedIds ?? [];
        const next = picked.includes(elementId)
          ? picked.filter((id) => id !== elementId)
          : [...picked, elementId];
        set({
          memberPickMode: {
            ...pick,
            pickedIds: next,
            updatedCount: next.length,
          },
          statuses:
            next.length > 0
              ? [
                  `${next.length} column${next.length === 1 ? "" : "s"} picked. Click Remove to delete them all.`,
                ]
              : ["Click columns in the viewport to pick them."],
          error: null,
        });
        return;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Update failed";
      set({ statuses: [], error: message });
    }
  },

  commitDeleteMemberPick: async () => {
    const pick = get().memberPickMode;
    if (!pick || pick.intent !== "delete") return;
    const ids = pick.pickedIds ?? [];
    if (ids.length === 0) return;

    set({
      isLoading: true,
      error: null,
      statuses: [`Removing ${ids.length} column(s)…`],
    });
    try {
      const result = await postDeleteMembers(
        get().projectElements,
        ids[0],
        "selection",
        ids,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        viewportMode: "inspect",
        memberPickMode: null,
        selectedElementId: null,
        selectionContext: null,
        isLoading: false,
        statuses: [result.message],
        error: null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Remove failed";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  finishMemberPickMode: () => {
    const pick = get().memberPickMode;
    if (!pick) return;
    if (pick.intent === "delete") {
      get().cancelMemberPickMode();
      return;
    }
    const { updatedCount } = pick;
    set({
      viewportMode: "inspect",
      memberPickMode: null,
      statuses:
        updatedCount > 0
          ? [`Updated ${updatedCount} column(s).`]
          : ["No columns were updated."],
    });
  },

  cancelMemberPickMode: () => {
    set({
      viewportMode: "inspect",
      memberPickMode: null,
      statuses: [],
    });
  },

  applyColumnProfile: async (profile, scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    const ids = resolveColumnTargetIds(get().projectElements, id, scope);
    if (ids.length === 0) return;
    set({ isLoading: true, error: null, statuses: ["Updating section…"] });
    try {
      const result = await postUpdateProfile(
        get().projectElements,
        profile,
        id,
        "selection",
        ids,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      const selected = elements.find((e) => e.id === id) ?? null;
      set({
        projectElements: elements,
        isLoading: false,
        statuses: [result.message],
        selectionContext: selected
          ? resolveSelectionContext(selected, elements, {
              trussType: trussTypeHint(get().shedAssemblyParams),
            })
          : get().selectionContext,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Profile update failed";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  applyColumnRotation: async (rotation, scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    const ids = new Set(
      resolveColumnTargetIds(get().projectElements, id, scope),
    );
    if (ids.size === 0) return;
    set((state) => {
      const elements = state.projectElements.map((el) =>
        ids.has(el.id) ? { ...el, rotation } : el,
      );
      const selected = elements.find((e) => e.id === id) ?? null;
      return {
        projectElements: elements,
        statuses: [`Rotation ${rotation}° applied to ${ids.size} column(s).`],
        selectionContext: selected
          ? resolveSelectionContext(selected, elements, {
              trussType: trussTypeHint(get().shedAssemblyParams),
            })
          : state.selectionContext,
      };
    });
  },

  applyColumnAlignment: async (alignment, scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    const ids = new Set(
      resolveColumnTargetIds(get().projectElements, id, scope),
    );
    if (ids.size === 0) return;
    set((state) => {
      const elements = state.projectElements.map((el) =>
        ids.has(el.id) ? { ...el, alignment } : el,
      );
      const selected = elements.find((e) => e.id === id) ?? null;
      return {
        projectElements: elements,
        statuses: [`Alignment “${alignment}” applied to ${ids.size} column(s).`],
        selectionContext: selected
          ? resolveSelectionContext(selected, elements, {
              trussType: trussTypeHint(get().shedAssemblyParams),
            })
          : state.selectionContext,
      };
    });
  },

  deleteColumnsScoped: async (scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    const ids = resolveColumnTargetIds(get().projectElements, id, scope);
    if (ids.length === 0) return;
    set({ isLoading: true, error: null, statuses: ["Removing columns…"] });
    try {
      const result = await postDeleteMembers(
        get().projectElements,
        id,
        "selection",
        ids,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        selectedElementId: null,
        selectionContext: null,
        isLoading: false,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Delete failed";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  setOnboardingLocation: async (lat, lon, label) => {
    if (get().uiPhase !== "onboarding" || get().isProposing) return;
    const site = placeholderSiteContext(lat, lon, label);
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
      const baseSite = get().siteContext;
      if (!baseSite) {
        set({ error: "Site data not loaded yet. Please wait and try again." });
        return;
      }

      const site = applySiteSurroundingsOverride(baseSite, SITE_BUILT_UP);
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
        error: null,
        messages,
      });
      return;
    }

    if (choice !== SITE_OPEN_INDUSTRIAL) return;

    const userLabel = surroundingsLabel(SITE_OPEN_INDUSTRIAL);
    const priorMessages = get().messages;
    const baseSite = get().siteContext;
    if (!baseSite) {
      set({ error: "Site data not loaded yet. Please wait and try again." });
      return;
    }

    const site = applySiteSurroundingsOverride(baseSite, SITE_OPEN_INDUSTRIAL);
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
      error: null,
      messages,
    });
  },

  confirmSiteMapPin: async (lat, lon) => {
    if (get().uiPhase !== "onboarding" || get().onboardingPhase !== "site_refine") {
      return;
    }
    const step1 = get().wizardStep1;
    const label = step1.location_label
      ? `${step1.location_label} (pinned)`
      : "Pinned site";

    const site = placeholderSiteContext(lat, lon, label);
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
        statuses: ["Fetching site climate and computing your proposal…"],
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
          siteContext: proposal.site_context ?? get().siteContext,
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
      messages: [],
      selectedElementId: null,
      selectionContext: null,
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
        const shedConfig = body as ShedAssemblyConfig;
        // Preserve per-bay truss/bracing from the caller (frame edits, truss type picks).
        apiPayload = {
          ...shedConfig,
          replace_existing: shedConfig.replace_existing ?? true,
          column_profile:
            profileOverrides.column_profile ?? shedConfig.column_profile,
          bracing_profile:
            profileOverrides.bracing_profile ?? shedConfig.bracing_profile,
          purlin_profile:
            profileOverrides.purlin_profile ?? shedConfig.purlin_profile,
          girt_profile: profileOverrides.girt_profile ?? shedConfig.girt_profile,
          sag_rod_profile:
            profileOverrides.sag_rod_profile ?? shedConfig.sag_rod_profile,
          base_plate_profile:
            profileOverrides.base_plate_profile ?? shedConfig.base_plate_profile,
        };
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
        selectionContext: selectedStillExists
          ? refreshSelectionContext(selectedId, elements, finalParams)
          : null,
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

  selectElement: (id) => {
    const elements = get().projectElements;
    const element = elements.find((e) => e.id === id);
    const mode = get().viewportMode;
    set({
      selectedElementId: id,
      selectionContext: element
        ? resolveSelectionContext(element, elements, {
            trussType: trussTypeHint(get().shedAssemblyParams),
          })
        : null,
      gridSelectionContext: null,
      viewportMode: mode === "pick_members_profile" ? mode : "inspect",
      placementIntent: null,
      pickedNodes: [],
    });
  },

  selectGridBay: (bayIndex) => {
    const ctx = resolveBaySelection(
      bayIndex,
      get().structuralGrid,
      get().projectElements,
      get().shedAssemblyParams,
    );
    if (!ctx) {
      set({ error: "Invalid bay selection." });
      return;
    }
    set({
      selectedElementId: null,
      selectionContext: null,
      gridSelectionContext: ctx,
      viewportMode: "inspect",
      placementIntent: null,
      pickedNodes: [],
      error: null,
    });
  },

  placeGridColumn: async (xAxis, zAxis, profile) => {
    const gridCtx = get().gridSelectionContext;
    if (!gridCtx) return;
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before placing grid members." });
      return;
    }
    const prof = (profile ?? gridCtx.defaultColumnProfile).trim().toUpperCase();
    const zLabels = zLabelsForGrid(get().structuralGrid);
    const trussed = inferTrussedZLabels(
      get().projectElements,
      zLabels,
      params.use_truss,
    );
    set({ isLoading: true, error: null, statuses: ["Placing column…"] });
    try {
      const result = await postPlaceGridColumn(get().projectElements, {
        x_axis: xAxis,
        z_axis: zAxis,
        profile: prof,
        grid: shedParamsToGridPlacement(params),
        trussed_z_labels: trussed,
        assembly_id: assemblyIdFromElements(get().projectElements),
      });
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        isLoading: false,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place column";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  placeGridTieBeam: async (xAxis, profile, elevation = "eave") => {
    const gridCtx = get().gridSelectionContext;
    if (!gridCtx) return;
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before placing grid members." });
      return;
    }
    const prof = (profile ?? gridCtx.defaultTieProfile).trim().toUpperCase();
    set({ isLoading: true, error: null, statuses: ["Placing tie beam…"] });
    try {
      const result = await postPlaceGridTieBeam(get().projectElements, {
        x_axis: xAxis,
        z_start: gridCtx.zStart,
        z_end: gridCtx.zEnd,
        profile: prof,
        elevation,
        grid: shedParamsToGridPlacement(params),
        assembly_id: assemblyIdFromElements(get().projectElements),
      });
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        isLoading: false,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place tie beam";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  startColumnPickMode: async (options) => {
    const gridCtx = get().gridSelectionContext;
    if (!gridCtx) {
      set({ error: "Select a grid bay first." });
      return;
    }
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before placing columns." });
      return;
    }
    const profile =
      options?.profile?.trim().toUpperCase() ||
      gridCtx.defaultColumnProfile;
    const tieProfile =
      options?.tieProfile?.trim().toUpperCase() ||
      gridCtx.defaultTieProfile;
    const pickMode: ColumnPickMode = {
      profile,
      tieProfile,
      addTieInBay: options?.addTieInBay ?? false,
      bayZStart: gridCtx.zStart,
      bayZEnd: gridCtx.zEnd,
    };
    set({
      viewportMode: "pick_column_nodes",
      columnPickMode: pickMode,
      groundPlacementNodes: [],
      error: null,
      statuses: ["Loading placement dots…"],
    });
    try {
      const zLabels = zLabelsForGrid(get().structuralGrid);
      const trussed = inferTrussedZLabels(
        get().projectElements,
        zLabels,
        params.use_truss,
      );
      const nodes = await fetchGroundPlacementNodes(
        {
          grid: shedParamsToGridPlacement(params),
          trussed_z_labels: trussed,
          truss_type: params.truss_type ?? "pratt",
          bay_z_start: gridCtx.zStart,
          bay_z_end: gridCtx.zEnd,
          extra_wall_offsets_mm: options?.extraWallOffsetsMm,
        },
        get().projectElements,
      );
      set({
        groundPlacementNodes: nodes,
        statuses: [
          `Click a green dot to place ${profile}. Gold = wall offset (e.g. A + 1200 mm). Teal = truss panel.`,
        ],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Could not load placement dots";
      set({
        viewportMode: "inspect",
        columnPickMode: null,
        groundPlacementNodes: [],
        statuses: [],
        error: message,
      });
    }
  },

  pickGroundPlacementNode: async (node) => {
    const pick = get().columnPickMode;
    const gridCtx = get().gridSelectionContext;
    if (!pick || get().viewportMode !== "pick_column_nodes") return;
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) return;

    const zLabels = zLabelsForGrid(get().structuralGrid);
    const trussed = inferTrussedZLabels(
      get().projectElements,
      zLabels,
      params.use_truss,
    );
    const connectTo =
      node.connect_to === "truss_bc"
        ? "truss_bc"
        : node.connect_to === "eave"
          ? "eave"
          : "auto";

    set({ isLoading: true, error: null, statuses: ["Placing column…"] });
    try {
      const result = await postPlaceGridColumn(get().projectElements, {
        x_axis: node.x_axis,
        z_axis: node.z_axis,
        profile: pick.profile,
        offset_mm: node.offset_mm,
        connect_to: connectTo,
        truss_type: params.truss_type ?? "pratt",
        add_tie_in_bay: pick.addTieInBay,
        tie_profile: pick.tieProfile,
        bay_z_start: gridCtx?.zStart ?? pick.bayZStart,
        bay_z_end: gridCtx?.zEnd ?? pick.bayZEnd,
        grid: shedParamsToGridPlacement(params),
        trussed_z_labels: trussed,
        assembly_id: assemblyIdFromElements(get().projectElements),
      });
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        isLoading: false,
        viewportMode: "inspect",
        columnPickMode: null,
        groundPlacementNodes: [],
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place column";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  cancelColumnPickMode: () =>
    set({
      viewportMode: "inspect",
      columnPickMode: null,
      groundPlacementNodes: [],
      statuses: [],
    }),

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
    const focusEl = focus
      ? projectElements.find((e) => e.id === focus)
      : null;
    set({
      selectedElementId: focus,
      selectionContext: focusEl
        ? resolveSelectionContext(focusEl, projectElements, {
            trussType: trussTypeHint(get().shedAssemblyParams),
          })
        : null,
      gridSelectionContext: null,
    });
  },

  clearSelection: () =>
    set({
      selectedElementId: null,
      selectionContext: null,
      gridSelectionContext: null,
      viewportMode: "inspect",
      placementIntent: null,
      pickedNodes: [],
      columnPickMode: null,
      groundPlacementNodes: [],
    }),

  startFramePlacement: () => {
    const ctx = get().selectionContext;
    if (ctx?.frameIndex === null || ctx?.frameIndex === undefined) {
      set({ error: "Select a column on a frame first." });
      return;
    }
    set({
      viewportMode: "pick_grid",
      placementIntent: "insert_frame",
      pickedNodes: [],
      error: null,
      statuses: [
        "Click a frame line along the length to insert a new portal frame (same spacing as this frame).",
      ],
    });
  },

  cancelGridPlacement: () =>
    set({
      viewportMode: "inspect",
      placementIntent: null,
      statuses: [],
    }),

  pickGridFrameLine: async (frameIndex) => {
    if (get().viewportMode !== "pick_grid") return;
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before adding frames." });
      return;
    }
    const afterBay = insertBayIndexForFrame(
      frameIndex,
      params.z_spans.length,
    );
    const next = insertFrameAfter(params, afterBay);
    set({
      viewportMode: "inspect",
      placementIntent: null,
      error: null,
      statuses: ["Adding portal frame…"],
    });
    try {
      await get().generateShedMacro(assemblyParamsToShedConfig(next));
      set({
        statuses: [],
        messages: [
          ...get().messages,
          {
            role: "assistant",
            content: `Added a portal frame along the length (bay spacing ${Math.round(
              params.z_spans[afterBay] ?? params.z_spans[0] ?? 6000,
            )} mm).`,
          },
        ],
      });
    } catch {
      set({ statuses: [], isMacroLoading: false });
    }
  },

  changeTrussType: async (trussType, scope = "frame") => {
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    if (!params) {
      set({ error: "Generate a shed before changing truss type." });
      return;
    }
    const ctx = get().selectionContext;
    const frameIndex = ctx?.frameIndex;
    const config =
      scope === "all" || frameIndex === null || frameIndex === undefined
        ? applyTrussTypeGlobally(params, trussType)
        : applyTrussTypeToFrame(params, frameIndex, trussType);
    set({ error: null, statuses: ["Rebuilding truss geometry…"] });
    try {
      await get().generateShedMacro(config);
      const selectedId = get().selectedElementId;
      set({
        statuses: [],
        selectionContext: refreshSelectionContext(
          selectedId,
          get().projectElements,
          get().shedAssemblyParams,
        ),
        messages: [
          ...get().messages,
          {
            role: "assistant",
            content:
              scope === "all"
                ? `All trussed frames now use a ${trussType} truss.`
                : `Frame updated to a ${trussType} truss.`,
          },
        ],
      });
    } catch {
      set({ statuses: [], isMacroLoading: false });
    }
  },

  switchFramePrimary: async (mode) => {
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    const ctx = get().selectionContext;
    const frameIndex = ctx?.frameIndex;
    if (!params || frameIndex === null || frameIndex === undefined) {
      set({ error: "Select a member on a portal frame first." });
      return;
    }
    const config =
      mode === "truss"
        ? switchFrameToTruss(params, frameIndex)
        : switchFrameToRafter(params, frameIndex);
    set({ error: null, statuses: ["Rebuilding frame…"] });
    try {
      await get().generateShedMacro(config);
      set({
        statuses: [],
        selectionContext: refreshSelectionContext(
          get().selectedElementId,
          get().projectElements,
          get().shedAssemblyParams,
        ),
        messages: [
          ...get().messages,
          {
            role: "assistant",
            content:
              mode === "truss"
                ? "Frame switched to truss primary."
                : "Frame switched to rafter primary.",
          },
        ],
      });
    } catch {
      set({ statuses: [], isMacroLoading: false });
    }
  },

  removeSelectedFrame: async () => {
    const params =
      get().shedAssemblyParams ??
      inferShedParamsFromElements(get().projectElements);
    const ctx = get().selectionContext;
    const frameIndex = ctx?.frameIndex;
    if (!params || frameIndex === null || frameIndex === undefined) {
      set({ error: "Select a member on a portal frame first." });
      return;
    }
    const next = removeFrameAt(params, frameIndex);
    if (!next) {
      set({ error: "Cannot remove the last frame line." });
      return;
    }
    set({
      error: null,
      statuses: ["Removing frame…"],
      selectedElementId: null,
      selectionContext: null,
    });
    try {
      await get().generateShedMacro(assemblyParamsToShedConfig(next));
      set({
        statuses: [],
        messages: [
          ...get().messages,
          {
            role: "assistant",
            content: "Portal frame removed and model rebuilt.",
          },
        ],
      });
    } catch {
      set({ statuses: [], isMacroLoading: false });
    }
  },

  startNodePlacement: async (intent, options) => {
    set({
      viewportMode: "pick_nodes",
      placementIntent: intent,
      placementProfile: options?.profile ?? null,
      pickedNodes: [],
      error: null,
      statuses: ["Loading connection points…"],
    });
    try {
      const nodes = await fetchSnapNodes(get().projectElements);
      const needed = intent === "full_x" ? 4 : 2;
      set({
        snapNodes: nodes,
        statuses: [
          `Pick ${needed} node${needed > 1 ? "s" : ""} in the viewport (${intent === "full_x" ? "X-brace corners" : "brace ends"}).`,
        ],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Could not load snap nodes";
      set({
        viewportMode: "inspect",
        placementIntent: null,
        placementProfile: null,
        statuses: [],
        error: message,
      });
    }
  },

  cancelNodePlacement: () =>
    set({
      viewportMode: "inspect",
      placementIntent: null,
      placementProfile: null,
      pickedNodes: [],
      statuses: [],
    }),

  pickSnapNode: async (node) => {
    if (get().viewportMode !== "pick_nodes" || !get().placementIntent) return;
    const picked: PickedNode = {
      snapId: node.id,
      x: node.x,
      y: node.y,
      z: node.z,
    };
    const nextPicked = [...get().pickedNodes, picked];
    const intent = get().placementIntent;
    const needed = intent === "full_x" ? 4 : 2;

    set({ pickedNodes: nextPicked });

    if (nextPicked.length < needed) {
      set({
        statuses: [
          `Node ${nextPicked.length}/${needed} selected — pick the next connection point.`,
        ],
      });
      return;
    }

    const ctx = get().selectionContext;
    const profile =
      get().placementProfile ?? ctx?.profile ?? "L70x70x7";
    const assemblyId = ctx?.assemblyId;
    set({ statuses: ["Placing bracing…"], isLoading: true, error: null });

    try {
      let result;
      if (intent === "full_x") {
        const [a, b, c, d] = nextPicked;
        result = await postPlaceBracingCross(
          get().projectElements,
          [
            { x: a.x, y: a.y, z: a.z },
            { x: b.x, y: b.y, z: b.z },
            { x: c.x, y: c.y, z: c.z },
            { x: d.x, y: d.y, z: d.z },
          ],
          profile,
          assemblyId,
        );
      } else {
        const [a, b] = nextPicked;
        result = await postPlaceBraceLeg(
          get().projectElements,
          { x: a.x, y: a.y, z: a.z },
          { x: b.x, y: b.y, z: b.z },
          profile,
          assemblyId,
        );
      }

      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        viewportMode: "inspect",
        placementIntent: null,
        placementProfile: null,
        pickedNodes: [],
        snapNodes: [],
        isLoading: false,
        statuses: [],
        messages: [
          ...get().messages,
          { role: "assistant", content: result.message },
        ],
        selectedElementId: result.changed_ids[0] ?? get().selectedElementId,
        selectionContext: (() => {
          const id = result.changed_ids[0];
          if (!id) return get().selectionContext;
          const el = elements.find((e) => e.id === id);
          return el
            ? resolveSelectionContext(el, elements, {
                trussType: trussTypeHint(get().shedAssemblyParams),
              })
            : null;
        })(),
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to place bracing";
      set({
        isLoading: false,
        statuses: [],
        error: message,
        pickedNodes: [],
        viewportMode: "inspect",
        placementIntent: null,
        placementProfile: null,
      });
    }
  },

  updateMemberProfile: async (profile, scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    set({ isLoading: true, error: null, statuses: ["Updating profile…"] });
    try {
      const result = await postUpdateProfile(
        get().projectElements,
        profile,
        id,
        scope,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      const selected = elements.find((e) => e.id === id) ?? null;
      set({
        projectElements: elements,
        isLoading: false,
        statuses: [result.message],
        selectionContext: selected
          ? resolveSelectionContext(selected, elements, {
              trussType: trussTypeHint(get().shedAssemblyParams),
            })
          : null,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Profile update failed";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

  deleteSelectedMembers: async (scope) => {
    const id = get().selectedElementId;
    if (!id) return;
    set({ isLoading: true, error: null, statuses: ["Removing members…"] });
    try {
      const result = await postDeleteMembers(
        get().projectElements,
        id,
        scope,
      );
      const elements = applyElementsFromApi(
        result.projectElements,
        get().projectElements,
      );
      set({
        projectElements: elements,
        selectedElementId: null,
        selectionContext: null,
        isLoading: false,
        statuses: [result.message],
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Delete failed";
      set({ isLoading: false, statuses: [], error: message });
    }
  },

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

    if (trimmed === WORKSPACE_PICK_ON_MODEL) {
      const profile = extractPendingProfileFromMessages(get().messages);
      if (profile) {
        get().startProfilePickMode(profile);
      }
      return;
    }

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
      const selectionPayload = selectionContextToPayload(get().selectionContext);
      const apiMessages = nextMessages.slice(-API_MESSAGE_WINDOW);
      const response = await postChat(
        apiMessages,
        projectState,
        selectedId,
        selectionPayload,
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

      const refreshedSelection = (() => {
        if (!selectedStillExists || !selectedId) return null;
        const el = elements.find((e) => e.id === selectedId);
        return el
          ? resolveSelectionContext(el, elements, {
              trussType: trussTypeHint(nextShedParams),
            })
          : null;
      })();

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
        selectionContext: refreshedSelection,
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
  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const memberPickMode = useProjectStore((state) => state.memberPickMode);
  if (memberPickMode?.intent === "delete") {
    return memberPickMode.pickedIds?.includes(elementId) ?? false;
  }
  return selectedElementId === elementId;
}

export function useSketchModeActive(): boolean {
  return useProjectStore((state) => state.viewportMode === "sketch");
}

export function useViewportSchematicMode(): boolean {
  const mode = useProjectStore((state) => state.viewportMode);
  return (
    mode === "pick_nodes" ||
    mode === "pick_grid" ||
    mode === "pick_panel" ||
    mode === "pick_column_nodes" ||
    mode === "sketch"
  );
}

export function useElementGhostOpacity(elementId: string): number {
  const viewportMode = useProjectStore((state) => state.viewportMode);
  const memberPickMode = useProjectStore((state) => state.memberPickMode);
  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const element = useProjectStore((state) =>
    state.projectElements.find((el) => el.id === elementId),
  );
  const schematic =
    viewportMode === "pick_nodes" ||
    viewportMode === "pick_column_nodes" ||
    viewportMode === "pick_panel" ||
    viewportMode === "sketch";
  const memberPickActive =
    viewportMode === "pick_members_profile" && memberPickMode !== null;
  if (memberPickActive) {
    return isColumnElement(element) ? 1 : 0.12;
  }
  if (!schematic) return 1;
  if (viewportMode === "sketch") {
    return SKETCH_GHOST_FACE_OPACITY;
  }
  if (elementId === selectedElementId) return 0.85;
  return 0.1;
}
