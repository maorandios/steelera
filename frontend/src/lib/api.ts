import type { ChatMessage, ChatResponse } from "@/types/chat";
import type { ProjectState } from "@/types/project";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function postChat(
  messages: ChatMessage[],
  projectState: ProjectState,
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      projectElements: projectState.projectElements,
      projectState,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Chat request failed (${res.status})`);
  }

  return res.json() as Promise<ChatResponse>;
}
