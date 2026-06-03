import type { ProjectState } from "@/types/project";

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatResponseMessage {
  role: "assistant";
  content: string;
}

export interface ChatResponse {
  message: ChatResponseMessage;
  statuses: string[];
  projectState: ProjectState;
}
