import type { SelectionContext } from "@/types/interaction";

export type SelectionContextPayload = {
  element_id: string;
  element_type: string;
  label: string;
  location_subtitle: string;
  profile: string | null;
  assembly_id: string | null;
  parent_assembly: string;
  frame_index: number | null;
  is_bracing: boolean;
};

export function selectionContextToPayload(
  ctx: SelectionContext | null,
): SelectionContextPayload | null {
  if (!ctx) return null;
  return {
    element_id: ctx.elementId,
    element_type: ctx.elementType,
    label: ctx.label,
    location_subtitle: ctx.locationSubtitle,
    profile: ctx.profile,
    assembly_id: ctx.assemblyId,
    parent_assembly: ctx.parentAssembly,
    frame_index: ctx.frameIndex,
    is_bracing: ctx.isBracing,
  };
}
