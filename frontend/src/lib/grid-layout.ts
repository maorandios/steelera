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
  const isTruss =
    Boolean(gd.use_truss) ||
    members.some((m) => m.element_type === "truss_web");
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
    mono_high_side: gd.mono_high_side === "A" ? "A" : "B",
    purlin_spacing: 1200,
    girt_spacing_mm: 1500,
    use_truss: isTruss,
    truss_type: (gd.truss_type && SELECTABLE_TRUSS_TYPES.has(gd.truss_type)
      ? gd.truss_type
      : "pratt") as Exclude<TrussType, "none">,
    use_bracing: Boolean(gd.x_bracing),
    use_gable_bracing: Boolean(gd.gable_bracing),
    use_roof_bracing: Boolean(gd.roof_bracing),
    use_sag_rods: Boolean(gd.sag_rods),
    use_haunches: Boolean(gd.haunches),
    use_fly_braces: Boolean(gd.fly_braces),
    use_base_plates: Boolean(gd.base_plates),
    use_bottom_chord_restraint: Boolean(gd.bottom_chord_restraint),
    generate_wall_girts: gd.generate_wall_girts ?? true,
    generate_tie_beams: gd.generate_tie_beams ?? true,
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
