"use client";

import { create } from "zustand";

import { postChat, postGenerateShed, type GenerateShedBody } from "@/lib/api";
import { gridLayoutToShedParams } from "@/lib/grid-layout";
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
  statuses: [],
  isLoading: false,
  isMacroLoading: false,
  error: null,

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
    const isGridLayout = "structural_members" in body && "grid_definition" in body;
    const fromBody = isGridLayout
      ? gridLayoutToShedParams(body as StructuralGridLayout)
      : shedConfigToAssemblyParams(body as ShedAssemblyConfig);
    const chatProfiles = extractProfilesFromMessages(get().messages);
    const params = mergeShedParams(
      mergeShedParams(get().shedAssemblyParams ?? DEFAULT_SHED_PARAMS, fromBody),
      {
        column_profile: chatProfiles.column_profile,
        bracing_profile: chatProfiles.bracing_profile,
        purlin_profile: chatProfiles.purlin_profile,
        girt_profile: chatProfiles.girt_profile,
        sag_rod_profile: chatProfiles.sag_rod_profile,
        base_plate_profile: chatProfiles.base_plate_profile,
      },
    );

    set({ isMacroLoading: true, error: null });

    try {
      const apiPayload = assemblyParamsToShedConfig(
        params,
        body.assembly_id ?? SHED_ASSEMBLY_ID,
      );
      apiPayload.replace_existing = body.replace_existing ?? true;
      const response = await postGenerateShed(apiPayload);
      const elements = (response.projectElements ?? []).map((element) =>
        normalizeElement(element),
      );
      const fromElements = inferShedParamsFromElements(elements);
      const finalParams = fromElements
        ? mergeShedParams(params, fromElements)
        : params;
      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );
      set({
        projectElements: elements,
        shedAssemblyParams: finalParams,
        structuralGrid: structuralGridFromShedParams(finalParams),
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
      } else if (incoming.length > 0) {
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
