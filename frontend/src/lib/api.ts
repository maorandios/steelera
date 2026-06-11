import type { SiteSurroundings } from "@/lib/site-surroundings";
import { abortAfterMs, formatApiError } from "@/lib/api-errors";
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
import type { ProfileScope, SnapNode } from "@/types/interaction";

export type IfcSchemaVersion = "IFC2X3" | "IFC4";

/**
 * Browser: same-origin `/api/*` (Next.js rewrite → FastAPI on :8000).
 * Avoids CORS and flaky localhost resolution on Windows.
 */
function apiBaseUrl(): string {
  if (typeof window !== "undefined") {
    // Same-origin /api/* → Next.js rewrite → FastAPI (avoids CORS on Windows).
    const direct = process.env.NEXT_PUBLIC_API_URL?.trim();
    return direct ? direct.replace(/\/$/, "") : "";
  }
  return (
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://127.0.0.1:8000"
  );
}

const CHAT_TIMEOUT_MS = 120_000;
const MACRO_TIMEOUT_MS = 60_000;
const SITE_TIMEOUT_MS = 90_000;
const PROPOSAL_TIMEOUT_MS = 120_000;
const MODEL_EDIT_TIMEOUT_MS = 45_000;
const SKETCH_TIMEOUT_MS = 30_000;
const EXPORT_TIMEOUT_MS = 90_000;

const BACKEND_HINT =
  "Cannot reach Steelera backend. Start it with: cd backend && python -m uvicorn main:app --reload --port 8000";

export type GenerateShedBody = ShedAssemblyConfig | StructuralGridLayout;

export async function postChat(
  messages: ChatMessage[],
  projectState: ProjectState,
  targetElementId?: string | null,
  selectionContext?: import("@/lib/selection-context-payload").SelectionContextPayload | null,
): Promise<ChatResponse> {
  const { signal, clear } = abortAfterMs(CHAT_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({
        messages,
        projectElements: projectState.projectElements,
        projectState,
        ...(targetElementId ? { target_element_id: targetElementId } : {}),
        ...(selectionContext ? { selection_context: selectionContext } : {}),
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      if (detail.includes("context_length_exceeded")) {
        throw new Error(
          "This model is too large for the AI context window. The server will use a compact summary — refresh and try again, or ask about a selected member only.",
        );
      }
      throw new Error(detail || `Chat request failed (${res.status})`);
    }

    return res.json() as Promise<ChatResponse>;
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Chat request timed out. Try a shorter message or refresh.",
        network: BACKEND_HINT,
        fallback: "Chat request failed.",
      }),
    );
  } finally {
    clear();
  }
}

export async function fetchSiteContext(
  lat: number,
  lon: number,
  label = "",
  surroundings: SiteSurroundings = "auto",
): Promise<SiteContext> {
  const { signal, clear } = abortAfterMs(SITE_TIMEOUT_MS);
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    surroundings,
    ...(label ? { label } : {}),
  });
  try {
    const res = await fetch(`${apiBaseUrl()}/api/site/context?${params}`, {
      signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Site context failed (${res.status})`);
    }
    return res.json() as Promise<SiteContext>;
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Site data request timed out. Please try again.",
        network: BACKEND_HINT,
        fallback: "Failed to load site data.",
      }),
    );
  } finally {
    clear();
  }
}

export async function geocodeLocation(query: string): Promise<GeocodeResult> {
  const { signal, clear } = abortAfterMs(SITE_TIMEOUT_MS);
  const params = new URLSearchParams({ q: query });
  try {
    const res = await fetch(`${apiBaseUrl()}/api/site/geocode?${params}`, {
      signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Geocoding failed (${res.status})`);
    }
    return res.json() as Promise<GeocodeResult>;
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Address lookup timed out. Try a shorter city name.",
        network: BACKEND_HINT,
        fallback: "Could not find that location.",
      }),
    );
  } finally {
    clear();
  }
}

export async function postProposeShed(
  body: ShedProposalRequest,
): Promise<ShedProposalResult> {
  const { signal, clear } = abortAfterMs(PROPOSAL_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/macro/propose-shed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Proposal failed (${res.status})`);
    }
    return res.json() as Promise<ShedProposalResult>;
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Proposal timed out. The backend may still be computing — try again.",
        network: BACKEND_HINT,
        fallback: "Failed to compute proposal.",
      }),
    );
  } finally {
    clear();
  }
}

export async function postGenerateShed(
  body: GenerateShedBody,
): Promise<GenerateShedResponse> {
  const { signal, clear } = abortAfterMs(MACRO_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/macro/generate-shed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
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
    throw new Error(
      formatApiError(err, {
        timeout: "Shed generation timed out.",
        network: BACKEND_HINT,
        fallback: "Failed to generate shed.",
      }),
    );
  } finally {
    clear();
  }
}

export async function postExportIfc(
  topology: StructuralTopology,
  schemaVersion: IfcSchemaVersion = "IFC4",
  filename?: string,
): Promise<Blob> {
  const { signal, clear } = abortAfterMs(EXPORT_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/export/ifc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
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
    throw new Error(
      formatApiError(err, {
        timeout: "IFC export timed out.",
        network: BACKEND_HINT,
        fallback: "IFC export failed.",
      }),
    );
  } finally {
    clear();
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

export type ModelEditResponse = {
  projectElements: import("@/types/project").ProjectElementMm[];
  message: string;
  changed_ids: string[];
};

async function postModelEdit<TBody extends Record<string, unknown>>(
  path: string,
  body: TBody,
): Promise<ModelEditResponse> {
  const { signal, clear } = abortAfterMs(MODEL_EDIT_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Model edit failed (${res.status})`);
    }
    const data = (await res.json()) as {
      projectElements: import("@/types/project").ProjectElementMm[];
      message: string;
      changed_ids: string[];
    };
    return {
      projectElements: data.projectElements,
      message: data.message,
      changed_ids: data.changed_ids ?? [],
    };
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Model update timed out.",
        network: BACKEND_HINT,
        fallback: "Model update failed.",
      }),
    );
  } finally {
    clear();
  }
}

export async function fetchSnapNodes(
  projectElements: import("@/types/project").ProjectElementMm[],
): Promise<SnapNode[]> {
  const { signal, clear } = abortAfterMs(MODEL_EDIT_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/model/snap-nodes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({ project_elements: projectElements }),
    });
    if (!res.ok) {
      throw new Error("Failed to load snap nodes");
    }
    const data = (await res.json()) as { nodes: SnapNode[] };
    return data.nodes ?? [];
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Loading connection points timed out.",
        network: BACKEND_HINT,
        fallback: "Failed to load snap nodes.",
      }),
    );
  } finally {
    clear();
  }
}

export async function fetchGroundPlacementNodes(
  body: {
    grid: import("@/types/grid-selection").GridPlacementContext;
    trussed_z_labels?: string[];
    truss_type?: string;
    bay_z_start?: string | null;
    bay_z_end?: string | null;
    extra_wall_offsets_mm?: number[];
  },
  projectElements: import("@/types/project").ProjectElementMm[],
): Promise<import("@/types/grid-selection").GroundPlacementNode[]> {
  const { signal, clear } = abortAfterMs(MODEL_EDIT_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/model/ground-placement-nodes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({
        project_elements: projectElements,
        ...body,
      }),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || "Failed to load placement nodes");
    }
    const data = (await res.json()) as {
      nodes: import("@/types/grid-selection").GroundPlacementNode[];
    };
    return data.nodes ?? [];
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Loading placement nodes timed out.",
        network: BACKEND_HINT,
        fallback: "Failed to load placement nodes.",
      }),
    );
  } finally {
    clear();
  }
}

export async function postUpdateProfile(
  projectElements: import("@/types/project").ProjectElementMm[],
  profile: string,
  referenceElementId: string,
  scope: ProfileScope,
  elementIds?: string[],
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/update-profile", {
    project_elements: projectElements,
    profile,
    reference_element_id: referenceElementId,
    scope,
    element_ids: elementIds ?? [],
  });
}

export async function postDeleteMembers(
  projectElements: import("@/types/project").ProjectElementMm[],
  referenceElementId: string,
  scope: ProfileScope,
  elementIds?: string[],
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/delete-members", {
    project_elements: projectElements,
    reference_element_id: referenceElementId,
    scope,
    element_ids: elementIds ?? [],
  });
}

export async function postPlaceGridColumn(
  projectElements: import("@/types/project").ProjectElementMm[],
  body: {
    x_axis: string;
    z_axis: string;
    profile: string;
    grid: import("@/types/grid-selection").GridPlacementContext;
    trussed_z_labels?: string[];
    assembly_id?: string | null;
    offset_mm?: Record<string, number>;
    connect_to?: "auto" | "truss_bc" | "eave";
    truss_type?: string;
    add_tie_in_bay?: boolean;
    tie_profile?: string | null;
    bay_z_start?: string | null;
    bay_z_end?: string | null;
  },
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/place-grid-column", {
    project_elements: projectElements,
    offset_mm: {},
    connect_to: "auto",
    truss_type: "pratt",
    add_tie_in_bay: false,
    ...body,
  });
}

export async function postPlaceGridTieBeam(
  projectElements: import("@/types/project").ProjectElementMm[],
  body: {
    x_axis: string;
    z_start: string;
    z_end: string;
    profile: string;
    elevation?: string;
    grid: import("@/types/grid-selection").GridPlacementContext;
    assembly_id?: string | null;
  },
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/place-grid-tie-beam", {
    project_elements: projectElements,
    elevation: body.elevation ?? "eave",
    ...body,
  });
}

export async function postPlaceBraceLeg(
  projectElements: import("@/types/project").ProjectElementMm[],
  start: { x: number; y: number; z: number },
  end: { x: number; y: number; z: number },
  profile?: string | null,
  assemblyId?: string | null,
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/place-brace-leg", {
    project_elements: projectElements,
    start_mm: start,
    end_mm: end,
    profile: profile ?? null,
    assembly_id: assemblyId ?? null,
  });
}

export async function postPlaceMemberBetweenPoints(
  projectElements: import("@/types/project").ProjectElementMm[],
  start: { x: number; y: number; z: number },
  end: { x: number; y: number; z: number },
  options?: {
    profile?: string | null;
    assemblyId?: string | null;
    elementType?: "bracing" | "tie_beam" | "purlin" | "beam";
  },
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/place-member-between-points", {
    project_elements: projectElements,
    start_mm: start,
    end_mm: end,
    profile: options?.profile ?? null,
    assembly_id: options?.assemblyId ?? null,
    element_type: options?.elementType ?? "bracing",
  });
}

export async function postPlaceBracingCross(
  projectElements: import("@/types/project").ProjectElementMm[],
  points: [
    { x: number; y: number; z: number },
    { x: number; y: number; z: number },
    { x: number; y: number; z: number },
    { x: number; y: number; z: number },
  ],
  profile?: string | null,
  assemblyId?: string | null,
): Promise<ModelEditResponse> {
  const [a, b, c, d] = points;
  return postModelEdit("/api/model/place-bracing-cross", {
    project_elements: projectElements,
    start_a_mm: a,
    end_a_mm: b,
    start_b_mm: c,
    end_b_mm: d,
    profile: profile ?? null,
    assembly_id: assemblyId ?? null,
  });
}

function sketchNodePayload(node: import("@/types/sketch").EnrichedSnapNode) {
  return {
    x: node.x,
    y: node.y,
    z: node.z,
    element_id: node.elementId,
    element_type: node.elementType,
    tier: node.tier,
    param_along_member: node.paramAlongMember,
  };
}

function mapIntentFromApi(
  intent: {
    kind: import("@/types/sketch").StructuralIntentKind;
    confidence: number;
    label: string;
    angle_class: import("@/types/sketch").StructuralIntentResult["angleClass"];
    span_mm: number;
    start_element_type: string;
    end_element_type: string;
    start_element_id: string;
    end_element_id: string;
  },
  startNode: import("@/types/sketch").EnrichedSnapNode,
  endNode: import("@/types/sketch").EnrichedSnapNode,
): import("@/types/sketch").StructuralIntentResult {
  return {
    kind: intent.kind,
    confidence: intent.confidence,
    label: intent.label,
    angleClass: intent.angle_class,
    spanMm: intent.span_mm,
    start: {
      elementType: intent.start_element_type,
      z: startNode.z,
      elementId: intent.start_element_id,
    },
    end: {
      elementType: intent.end_element_type,
      z: endNode.z,
      elementId: intent.end_element_id,
    },
  };
}

export async function fetchStructuralAdvise(body: {
  trigger?: "sketch" | "selection";
  projectElements: import("@/types/project").ProjectElementMm[];
  startNode?: import("@/types/sketch").EnrichedSnapNode;
  endNode?: import("@/types/sketch").EnrichedSnapNode;
  selectionContext?: import("@/lib/selection-context-payload").SelectionContextPayload | null;
  intentOverride?: import("@/types/sketch").StructuralIntentKind | null;
  siteContext?: SiteContext | null;
  shedParams?: Record<string, unknown> | null;
  xCoordsMm?: number[];
  zCoordsMm?: number[];
}): Promise<import("@/types/structural-advise").StructuralAdviseResult> {
  const { signal, clear } = abortAfterMs(SKETCH_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBaseUrl()}/api/structural/advise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({
        trigger: body.trigger ?? (body.selectionContext ? "selection" : "sketch"),
        project_elements: body.projectElements,
        start_node: body.startNode ? sketchNodePayload(body.startNode) : null,
        end_node: body.endNode ? sketchNodePayload(body.endNode) : null,
        selection_context: body.selectionContext ?? null,
        intent_override: body.intentOverride ?? null,
        site_context: body.siteContext ?? null,
        shed_params: body.shedParams ?? null,
        x_coords_mm: body.xCoordsMm ?? null,
        z_coords_mm: body.zCoordsMm ?? null,
      }),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Structural advise failed (${res.status})`);
    }
    const data = (await res.json()) as {
      summary: string;
      intent: Parameters<typeof mapIntentFromApi>[0] | null;
      operations: import("@/types/structural-advise").OperationProposal[];
      recommended_operation_id: string | null;
      profiles: import("@/types/sketch").SketchProfileOption[];
      scope_suggestion: import("@/types/sketch").SketchApplyScope;
      scope_reason: string;
      alternatives: import("@/types/sketch").StructuralIntentKind[];
      ai_available: boolean;
    };
    return {
      summary: data.summary,
      intent:
        data.intent && body.startNode && body.endNode
          ? mapIntentFromApi(data.intent, body.startNode, body.endNode)
          : null,
      operations: data.operations ?? [],
      recommended_operation_id: data.recommended_operation_id,
      profiles: data.profiles ?? [],
      scope_suggestion: data.scope_suggestion,
      scope_reason: data.scope_reason,
      alternatives: data.alternatives ?? [],
      ai_available: data.ai_available,
    };
  } catch (err) {
    throw new Error(
      formatApiError(err, {
        timeout: "Structural analysis timed out.",
        network: BACKEND_HINT,
        fallback: "Failed to get structural advice.",
      }),
    );
  } finally {
    clear();
  }
}

export async function fetchSketchAnalysis(body: {
  projectElements: import("@/types/project").ProjectElementMm[];
  startNode: import("@/types/sketch").EnrichedSnapNode;
  endNode: import("@/types/sketch").EnrichedSnapNode;
  intentOverride?: import("@/types/sketch").StructuralIntentKind | null;
  siteContext?: SiteContext | null;
  shedParams?: Record<string, unknown> | null;
  xCoordsMm?: number[];
  zCoordsMm?: number[];
}): Promise<import("@/types/sketch").SketchAnalysisResult> {
  const advise = await fetchStructuralAdvise({
    trigger: "sketch",
    ...body,
  });
  if (!advise.intent) {
    throw new Error("No intent in structural advise response");
  }
  return {
    intent: advise.intent,
    profiles: advise.profiles,
    message: advise.summary,
    scope_suggestion: advise.scope_suggestion,
    scope_reason: advise.scope_reason,
    alternatives: advise.alternatives,
    ai_available: advise.ai_available,
    operations: advise.operations,
    recommended_operation_id: advise.recommended_operation_id,
    summary: advise.summary,
  };
}

export async function postPlaceXBraceFromLeg(
  projectElements: import("@/types/project").ProjectElementMm[],
  start: { x: number; y: number; z: number },
  end: { x: number; y: number; z: number },
  options?: { profile?: string | null; assemblyId?: string | null },
): Promise<ModelEditResponse> {
  return postModelEdit("/api/model/place-x-brace-from-leg", {
    project_elements: projectElements,
    start_mm: start,
    end_mm: end,
    profile: options?.profile ?? null,
    assembly_id: options?.assemblyId ?? null,
  });
}
