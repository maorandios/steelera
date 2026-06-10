import type { SiteSurroundings } from "@/lib/site-surroundings";
import type { GeocodeResult, SiteContext } from "@/types/site";
import type { ChatMessage, ChatResponse } from "@/types/chat";
import type {
  ShedProposalRequest,
  ShedProposalResult,
} from "@/types/wizard";
import type { GenerateShedResponse } from "@/types/macro";
import type { ShedAssemblyConfig } from "@/types/shed-config";
import type { StructuralGridLayout } from "@/types/spatial-grid";
import type { StructuralTopology } from "@/types/ifc-topology";
import type { ProjectState } from "@/types/project";

export type IfcSchemaVersion = "IFC2X3" | "IFC4";

/**
 * Browser: same-origin `/api/*` (Next.js rewrite → FastAPI on :8000).
 * Avoids CORS and flaky localhost resolution on Windows.
 */
function apiBaseUrl(): string {
  // Call FastAPI directly in the browser — Next.js rewrites time out on long chat (~30s).
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  }
  return (
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://127.0.0.1:8000"
  );
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

const MACRO_TIMEOUT_MS = 60_000;

export type GenerateShedBody = ShedAssemblyConfig | StructuralGridLayout;

const SITE_TIMEOUT_MS = 45_000;

export async function fetchSiteContext(
  lat: number,
  lon: number,
  label = "",
  surroundings: SiteSurroundings = "auto",
): Promise<SiteContext> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), SITE_TIMEOUT_MS);
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    surroundings,
    ...(label ? { label } : {}),
  });
  try {
    const res = await fetch(`${apiBaseUrl()}/api/site/context?${params}`, {
      signal: controller.signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Site context failed (${res.status})`);
    }
    return res.json() as Promise<SiteContext>;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function geocodeLocation(query: string): Promise<GeocodeResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), SITE_TIMEOUT_MS);
  const params = new URLSearchParams({ q: query });
  try {
    const res = await fetch(`${apiBaseUrl()}/api/site/geocode?${params}`, {
      signal: controller.signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Geocoding failed (${res.status})`);
    }
    return res.json() as Promise<GeocodeResult>;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function postProposeShed(
  body: ShedProposalRequest,
): Promise<ShedProposalResult> {
  const res = await fetch(`${apiBaseUrl()}/api/macro/propose-shed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Proposal failed (${res.status})`);
  }
  return res.json() as Promise<ShedProposalResult>;
}

export async function postGenerateShed(
  body: GenerateShedBody,
): Promise<GenerateShedResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), MACRO_TIMEOUT_MS);

  try {
    const res = await fetch(`${apiBaseUrl()}/api/macro/generate-shed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const detail = await res.text();
      let message = detail || `Shed macro failed (${res.status})`;
      try {
        const parsed = JSON.parse(detail) as { detail?: unknown };
        if (typeof parsed.detail === "string") {
          message = parsed.detail;
        }
      } catch {
        /* plain text error body */
      }
      throw new Error(message);
    }

    return res.json() as Promise<GenerateShedResponse>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Shed generation timed out.");
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

const EXPORT_TIMEOUT_MS = 90_000;

export async function postExportIfc(
  topology: StructuralTopology,
  schemaVersion: IfcSchemaVersion = "IFC4",
  filename?: string,
): Promise<Blob> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), EXPORT_TIMEOUT_MS);

  try {
    const res = await fetch(`${apiBaseUrl()}/api/export/ifc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        structural_topology: topology,
        schema_version: schemaVersion,
        ...(filename ? { filename } : {}),
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      let message = detail || `IFC export failed (${res.status})`;
      try {
        const parsed = JSON.parse(detail) as { detail?: unknown };
        if (typeof parsed.detail === "string") {
          message = parsed.detail;
        }
      } catch {
        /* plain text */
      }
      throw new Error(message);
    }

    return res.blob();
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("IFC export timed out.");
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

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
