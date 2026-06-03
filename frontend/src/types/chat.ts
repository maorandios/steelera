import type { ProjectElementMm, ProjectState } from "@/types/project";

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
  projectElements: ProjectElementMm[];
  projectState?: ProjectState;
}
