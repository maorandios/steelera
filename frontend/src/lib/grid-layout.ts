import { formatSpansInput, totalFromSpans, type ShedAssemblyParams } from "@/lib/shed-assembly";
import type { ShedAssemblyConfig } from "@/types/shed-config";
import type { StructuralGridLayout } from "@/types/spatial-grid";

/** Infer sidebar params from a resolved grid layout (spans + global heights). */
export function gridLayoutToShedParams(
  layout: StructuralGridLayout,
): ShedAssemblyParams {
  const gd = layout.grid_definition;
  const x = gd.x_spans;
  const z = gd.z_spans;
  return {
    x_spans: x,
    z_spans: z,
    x_spans_input: formatSpansInput(x),
    z_spans_input: formatSpansInput(z),
    width: totalFromSpans(x),
    length: totalFromSpans(z),
    height: gd.height_mm,
    roof_pitch_deg: gd.roof_style === "flat" ? 0 : gd.roof_pitch_deg,
    roof_style: gd.roof_style,
    purlin_spacing: 1200,
    girt_spacing_mm: 1500,
    use_truss: layout.structural_members.some((m) => m.element_type === "truss_web"),
    use_bracing: layout.structural_members.some((m) => m.element_type === "bracing"),
    use_sag_rods: layout.structural_members.some((m) => m.element_type === "sag_rod"),
    generate_wall_girts: layout.structural_members.some(
      (m) => m.element_type === "wall_girt",
    ),
    generate_tie_beams: layout.structural_members.some(
      (m) => m.element_type === "tie_beam",
    ),
  };
}

export function isStructuralGridLayout(
  body: ShedAssemblyConfig | StructuralGridLayout,
): body is StructuralGridLayout {
  return "structural_members" in body && "grid_definition" in body;
}
