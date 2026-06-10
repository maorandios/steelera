import { viewportTheme } from "@/lib/viewport-theme";
import type { ProjectElementMm } from "@/types/project";

export type ElementDisplayRole = "primary" | "secondary" | "bracing";

const PRIMARY_TYPES = new Set([
  "column",
  "rafter",
  "truss_chord",
  "tie_beam",
  "haunch",
  "base_plate",
]);

const SECONDARY_TYPES = new Set([
  "purlin",
  "wall_girt",
  "truss_web",
  "sag_rod",
]);

const BRACING_TYPES = new Set(["bracing", "x_brace", "fly_brace"]);

function roleFromId(id: string): ElementDisplayRole | null {
  if (/-brace-/.test(id) || id.includes("fly-brace")) return "bracing";
  if (/-truss-web-/.test(id)) return "secondary";
  if (/-truss-(?:TC|BC|post)-/.test(id)) return "primary";
  if (/-purlin-/.test(id) || id.startsWith("shed-purlin")) return "secondary";
  if (/-girt-/.test(id) || /-gablegirt-/.test(id)) return "secondary";
  if (/-sag-/.test(id) || id.startsWith("shed-sag")) return "secondary";
  if (/-col-/.test(id) || id.startsWith("shed-col")) return "primary";
  if (/-rafter-/.test(id) || id.startsWith("shed-raf")) return "primary";
  if (/-tie-/.test(id)) return "primary";
  if (/-haunch-/.test(id)) return "primary";
  if (/-plate-/.test(id)) return "primary";
  return null;
}

function roleFromShape(shape: ProjectElementMm["shape_type"]): ElementDisplayRole {
  if (shape === "C-channel" || shape === "Zed") return "secondary";
  if (shape === "Angle" || shape === "Pipe" || shape === "CHS") return "bracing";
  if (shape === "Haunch") return "primary";
  return "primary";
}

export function resolveElementDisplayRole(
  element: ProjectElementMm,
): ElementDisplayRole {
  const et = element.element_type ?? "";
  if (PRIMARY_TYPES.has(et)) return "primary";
  if (SECONDARY_TYPES.has(et)) return "secondary";
  if (BRACING_TYPES.has(et)) return "bracing";

  const fromId = roleFromId(element.id);
  if (fromId) return fromId;

  return roleFromShape(element.shape_type);
}

export function elementDisplayColor(element: ProjectElementMm): string {
  const role = resolveElementDisplayRole(element);
  return viewportTheme.steel.roles[role];
}
