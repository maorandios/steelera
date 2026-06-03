"use client";

import { create } from "zustand";

import { postChat } from "@/lib/api";
import type { ChatMessage } from "@/types/chat";
import type {
  ElementAlignment,
  ElementRotation,
  ProjectElementMm,
} from "@/types/project";
import { emptyProjectState, normalizeElement } from "@/types/project";

/** Keep API payloads bounded so long chats stay responsive. */
const API_MESSAGE_WINDOW = 24;

function mergeElementsFromApi(
  incoming: ProjectElementMm[],
  existing: ProjectElementMm[],
): ProjectElementMm[] {
  return incoming.map((element) => {
    const prior = existing.find((item) => item.id === element.id);
    return normalizeElement({
      ...element,
      rotation: prior?.rotation ?? element.rotation,
      alignment: prior?.alignment ?? element.alignment,
    });
  });
}

interface ProjectStore {
  messages: ChatMessage[];
  projectElements: ProjectElementMm[];
  selectedElementId: string | null;
  statuses: string[];
  isLoading: boolean;
  error: string | null;
  viewportExpanded: boolean;
  sendMessage: (content: string) => Promise<void>;
  toggleViewport: () => void;
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
  selectedElementId: null,
  statuses: [],
  isLoading: false,
  error: null,
  viewportExpanded: false,

  toggleViewport: () =>
    set((state) => ({ viewportExpanded: !state.viewportExpanded })),

  clearError: () => set({ error: null }),

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
      const elements = mergeElementsFromApi(incoming, get().projectElements);
      const selectedStillExists = elements.some(
        (element) => element.id === selectedId,
      );

      set({
        messages: [...nextMessages, response.message],
        projectElements: elements,
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
