"use client";

import { create } from "zustand";

import { postChat, postGenerateShed } from "@/lib/api";
import {
  inferShedParamsFromElements,
  mergeShedParams,
  shedParamsToApiPayload,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import {
  buildStructuralGridState,
  DEFAULT_STRUCTURAL_GRID,
  structuralGridFromShedParams,
  type StructuralGridState,
} from "@/lib/structural-grid";
import type { ChatMessage } from "@/types/chat";
import type {
  ElementAlignment,
  ElementRotation,
  ProjectElementMm,
} from "@/types/project";
import { emptyProjectState, normalizeElement } from "@/types/project";

/** Keep API payloads bounded so long chats stay responsive. */
const API_MESSAGE_WINDOW = 24;

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
  generateShedMacro: (params: ShedAssemblyParams) => Promise<void>;
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
        "Welcome to Steelera (Milestone 1). Describe members to add, e.g. “Add a 6 m box beam at the origin”.",
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

  generateShedMacro: async (params) => {
    if (get().isMacroLoading || get().isLoading) return;

    const selectedId = get().selectedElementId;

    set({ isMacroLoading: true, error: null });

    try {
      const response = await postGenerateShed({
        assembly_id: "shed_1",
        replace_existing: true,
        ...shedParamsToApiPayload(params),
      });
      const elements = (response.projectElements ?? []).map((element) =>
        normalizeElement(element),
      );
      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );
      set({
        projectElements: elements,
        shedAssemblyParams: params,
        structuralGrid: structuralGridFromShedParams(params),
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
    await get().generateShedMacro(mergeShedParams(current, partial));
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
      const incoming =
        response.projectElements ??
        response.projectState?.projectElements ??
        [];
      const elements = applyElementsFromApi(incoming, get().projectElements);
      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );
      const inferredShed = inferShedParamsFromElements(elements);

      set({
        messages: [...nextMessages, response.message],
        projectElements: elements,
        shedAssemblyParams: inferredShed ?? get().shedAssemblyParams,
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
