import type { ChatMessage, ChatResponse } from "@/types/chat";
import type { ProjectState } from "@/types/project";

/**
 * Browser: same-origin `/api/*` (Next.js rewrite → FastAPI on :8000).
 * Avoids CORS and flaky localhost resolution on Windows.
 */
function apiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

const CHAT_TIMEOUT_MS = 120_000;

export async function postChat(
  messages: ChatMessage[],
  projectState: ProjectState,
  targetElementId?: string | null,
): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

  try {
    const res = await fetch(`${apiBaseUrl()}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        messages,
        projectElements: projectState.projectElements,
        projectState,
        ...(targetElementId ? { target_element_id: targetElementId } : {}),
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Chat request failed (${res.status})`);
    }

    return res.json() as Promise<ChatResponse>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Chat request timed out. Try a shorter message or refresh.");
    }
    if (err instanceof TypeError) {
      throw new Error(
        "Cannot reach Steelera backend. Start it with: cd backend && python -m uvicorn main:app --reload --port 8000",
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}
