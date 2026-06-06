import { formatSpansInput, totalFromSpans, type ShedAssemblyParams } from "@/lib/shed-assembly";
import type { ShedAssemblyConfig, TrussType } from "@/types/shed-config";
import type { StructuralGridLayout, StructuralMember } from "@/types/spatial-grid";

const SELECTABLE_TRUSS_TYPES: ReadonlySet<string> = new Set([
  "pratt",
  "howe",
  "warren",
  "fink",
  "king_post",
  "queen_post",
  "scissor",
]);

function profileFromMembers(
  members: StructuralMember[],
  elementType: StructuralMember["element_type"],
): string | undefined {
  return members.find((m) => m.element_type === elementType)?.profile;
}

/** Infer sidebar params from a resolved grid layout (spans + global heights). */
export function gridLayoutToShedParams(
  layout: StructuralGridLayout,
): ShedAssemblyParams {
  const gd = layout.grid_definition;
  const members = layout.structural_members;
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
    truss_type: (gd.truss_type && SELECTABLE_TRUSS_TYPES.has(gd.truss_type)
      ? gd.truss_type
      : "pratt") as Exclude<TrussType, "none">,
    use_bracing: layout.structural_members.some((m) => m.element_type === "bracing"),
    use_gable_bracing: layout.structural_members.some((m) =>
      m.id.includes("-brace-end-"),
    ),
    use_roof_bracing: layout.structural_members.some((m) =>
      m.id.includes("-brace-roof-"),
    ),
    use_sag_rods: layout.structural_members.some((m) => m.element_type === "sag_rod"),
    use_haunches: layout.structural_members.some((m) => m.element_type === "haunch"),
    use_fly_braces: layout.structural_members.some((m) => m.element_type === "fly_brace"),
    use_base_plates: layout.structural_members.some(
      (m) => m.element_type === "base_plate",
    ),
    use_bottom_chord_restraint: layout.structural_members.some((m) =>
      m.id.includes("-bctie-"),
    ),
    generate_wall_girts: layout.structural_members.some(
      (m) => m.element_type === "wall_girt",
    ),
    generate_tie_beams: layout.structural_members.some(
      (m) => m.element_type === "tie_beam",
    ),
    column_profile: gd.column_profile ?? profileFromMembers(members, "column"),
    bracing_profile: gd.bracing_profile ?? profileFromMembers(members, "bracing"),
    purlin_profile: gd.purlin_profile ?? profileFromMembers(members, "purlin"),
    girt_profile: gd.girt_profile ?? profileFromMembers(members, "wall_girt"),
    sag_rod_profile: gd.sag_rod_profile ?? profileFromMembers(members, "sag_rod"),
    base_plate_profile: gd.base_plate_profile,
  };
}

export function isStructuralGridLayout(
  body: ShedAssemblyConfig | StructuralGridLayout,
): body is StructuralGridLayout {
  return "structural_members" in body && "grid_definition" in body;
}
