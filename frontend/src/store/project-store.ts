"use client";

import { create } from "zustand";

import { postChat } from "@/lib/api";
import type { ChatMessage } from "@/types/chat";
import { emptyProjectState, type ProjectState } from "@/types/project";

interface ProjectStore {
  messages: ChatMessage[];
  projectState: ProjectState;
  statuses: string[];
  isLoading: boolean;
  error: string | null;
  viewportExpanded: boolean;
  sendMessage: (content: string) => Promise<void>;
  toggleViewport: () => void;
  clearError: () => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  messages: [
    {
      role: "assistant",
      content:
        "Welcome to Steelera. Describe a structure (e.g. “Build a 30×12 m shed, 4.5 m eave height”) and I’ll generate steel members in 3D.",
    },
  ],
  projectState: emptyProjectState(),
  statuses: [],
  isLoading: false,
  error: null,
  viewportExpanded: false,

  toggleViewport: () =>
    set((s) => ({ viewportExpanded: !s.viewportExpanded })),

  clearError: () => set({ error: null }),

  sendMessage: async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || get().isLoading) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...get().messages, userMessage];

    set({
      messages: nextMessages,
      isLoading: true,
      statuses: ["Sending..."],
      error: null,
    });

    try {
      const response = await postChat(nextMessages, get().projectState);
      set({
        messages: [...nextMessages, response.message],
        projectState: response.projectState,
        statuses: response.statuses,
        isLoading: false,
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
