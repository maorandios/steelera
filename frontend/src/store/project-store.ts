"use client";

import { create } from "zustand";

import { postChat, postGenerateShed, type GenerateShedBody } from "@/lib/api";
import {
  extractGridIntentFromMessages,
  mergeGridDefinitionWithIntent,
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
import { highlightedElementIds } from "@/lib/assembly-highlight";
import { checklistPayloadToShedParams } from "@/lib/shed-checklist";
import type { StructuralTopology } from "@/types/ifc-topology";
import type {
  ChatMessage,
  ShedChecklistPayload,
  ShedChecklistSelections,
} from "@/types/chat";
import type {
  ElementAlignment,
  ElementRotation,
  ProjectElementMm,
} from "@/types/project";
import { emptyProjectState, normalizeElement } from "@/types/project";

/** Keep API payloads bounded so long chats stay responsive. */
const API_MESSAGE_WINDOW = 24;

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

interface ProjectStore {
  messages: ChatMessage[];
  projectElements: ProjectElementMm[];
  shedAssemblyParams: ShedAssemblyParams | null;
  structuralGrid: StructuralGridState;
  selectedElementId: string | null;
  highlightedElementIds: string[];
  structuralTopology: StructuralTopology | null;
  statuses: string[];
  isLoading: boolean;
  isMacroLoading: boolean;
  error: string | null;
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
  messages: [
    {
      role: "assistant",
      content:
        "Welcome to Steelera. Describe a portal-frame shed — I'll place members on the spatial grid (axes A,B,… and 1,2,…) and resolve them to 3D. Example: “Build 10×30 m duo shed, 4 m eave, 10° pitch, Pratt truss in bay 1.”",
    },
  ],
  projectElements: emptyProjectState().projectElements,
  shedAssemblyParams: null,
  structuralGrid: { ...DEFAULT_STRUCTURAL_GRID },
  selectedElementId: null,
  highlightedElementIds: [],
  structuralTopology: null,
  statuses: [],
  isLoading: false,
  isMacroLoading: false,
  error: null,

  setProjectElements: (elements) =>
    set({
      projectElements: elements.map((element) => normalizeElement(element)),
      selectedElementId: null,
      highlightedElementIds: [],
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
    const params = mergeShedParams(
      mergeShedParams(get().shedAssemblyParams ?? DEFAULT_SHED_PARAMS, fromBody),
      {
        column_profile: chatProfiles.column_profile,
        bracing_profile: chatProfiles.bracing_profile,
        purlin_profile: chatProfiles.purlin_profile,
        girt_profile: chatProfiles.girt_profile,
        sag_rod_profile: chatProfiles.sag_rod_profile,
        base_plate_profile: chatProfiles.base_plate_profile,
        use_truss: chatIntent.use_truss ?? fromBody.use_truss,
        truss_type: chatIntent.truss_type ?? fromBody.truss_type,
        roof_style: chatIntent.roof_style ?? fromBody.roof_style,
        roof_pitch_deg: chatIntent.roof_pitch_deg ?? fromBody.roof_pitch_deg,
        use_bracing: chatIntent.x_bracing ?? fromBody.use_bracing,
        use_gable_bracing: chatIntent.gable_bracing ?? fromBody.use_gable_bracing,
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
        const gd = mergeGridDefinitionWithIntent(
          layout.grid_definition,
          chatIntent,
        );
        apiPayload = {
          ...layout,
          replace_existing: layout.replace_existing ?? true,
          structural_members: [],
          grid_definition: {
            ...gd,
            use_truss: params.use_truss || Boolean(gd.use_truss),
            truss_type: params.use_truss
              ? params.truss_type
              : ((gd.truss_type ?? "none") as typeof gd.truss_type),
            mono_high_side: gd.mono_high_side ?? params.mono_high_side,
            roof_style: params.roof_style ?? gd.roof_style,
            roof_pitch_deg: params.roof_pitch_deg ?? gd.roof_pitch_deg,
            height_mm: gd.height_mm ?? params.height,
            x_bracing: params.use_bracing || Boolean(gd.x_bracing),
            gable_bracing: params.use_gable_bracing || Boolean(gd.gable_bracing),
            roof_bracing: params.use_roof_bracing || Boolean(gd.roof_bracing),
            sag_rods: params.use_sag_rods || Boolean(gd.sag_rods),
            haunches: params.use_haunches || Boolean(gd.haunches),
            fly_braces: params.use_fly_braces || Boolean(gd.fly_braces),
            base_plates: params.use_base_plates || Boolean(gd.base_plates),
            bottom_chord_restraint:
              params.use_bottom_chord_restraint ||
              Boolean(gd.bottom_chord_restraint),
            generate_wall_girts:
              params.generate_wall_girts ?? gd.generate_wall_girts ?? true,
            generate_tie_beams:
              params.generate_tie_beams ?? gd.generate_tie_beams ?? true,
            column_profile: params.column_profile ?? gd.column_profile,
            bracing_profile: params.bracing_profile ?? gd.bracing_profile,
            purlin_profile: params.purlin_profile ?? gd.purlin_profile,
            girt_profile: params.girt_profile ?? gd.girt_profile,
            sag_rod_profile: params.sag_rod_profile ?? gd.sag_rod_profile,
            base_plate_profile: params.base_plate_profile ?? gd.base_plate_profile,
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
      const highlightForSelection = selectedStillExists && selectedId
        ? Array.from(
            highlightedElementIds(selectedId, topology, elements),
          )
        : [];
      set({
        projectElements: elements,
        shedAssemblyParams: finalParams,
        structuralGrid: structuralGridFromShedParams(finalParams),
        structuralTopology: topology,
        isMacroLoading: false,
        selectedElementId: selectedStillExists ? selectedId : null,
        highlightedElementIds: highlightForSelection,
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
    const { structuralTopology, projectElements } = get();
    set({
      selectedElementId: id,
      highlightedElementIds: Array.from(
        highlightedElementIds(id, structuralTopology, projectElements),
      ),
    });
  },

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
    set({
      selectedElementId: focus,
      highlightedElementIds: ids,
    });
  },

  clearSelection: () =>
    set({ selectedElementId: null, highlightedElementIds: [] }),

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

      if (gridLayoutRaw) {
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
        highlightedElementIds:
          selectedStillExists && selectedId
            ? Array.from(
                highlightedElementIds(
                  selectedId,
                  get().structuralTopology,
                  elements,
                ),
              )
            : [],
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
  const highlighted = useProjectStore((state) => state.highlightedElementIds);
  const selected = useProjectStore((state) => state.selectedElementId);
  if (highlighted.length > 0) {
    return highlighted.includes(elementId);
  }
  return selected === elementId;
}
