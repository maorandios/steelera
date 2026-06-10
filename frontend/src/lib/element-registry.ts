import type {
  ProfileScope,
  SelectionAction,
  SelectionActionId,
  SelectionContext,
} from "@/types/interaction";
import { TRUSS_TYPE_OPTIONS } from "@/types/shed-config";

/** Canonical kinds for viewport selection — one registry entry each. */
export type ElementKind =
  | "column"
  | "rafter"
  | "truss_chord"
  | "truss_web"
  | "purlin"
  | "wall_girt"
  | "bracing"
  | "tie_beam"
  | "generic";

export type SuggestedPrompt = {
  label: string;
  message: string;
};

export type ProfileScopeOption = {
  scope: ProfileScope | "pick_members";
  label: string;
};

export type ElementRegistryEntry = {
  kind: ElementKind;
  profileCatalog: readonly string[];
  doActions: SelectionAction[];
  advicePrompts: (ctx: SelectionContext) => SuggestedPrompt[];
  profileScopes: (ctx: SelectionContext) => ProfileScopeOption[];
};

export const BRACING_PROFILE_OPTIONS = [
  "L50x50",
  "L60x60x6",
  "L70x70x7",
  "L100x100x10",
  "L120x120x10",
] as const;

export const COLUMN_PROFILE_OPTIONS = [
  "HEA160",
  "HEA180",
  "HEA200",
  "HEA240",
  "HEA260",
  "HEA320",
  "HEA360",
  "HEA400",
  "HEA450",
  "SHS200x200x8",
  "SHS300x300x10",
] as const;

export const TRUSS_CHORD_PROFILE_OPTIONS = [
  "IPE180",
  "IPE200",
  "IPE240",
  "SHS120x120x6",
  "SHS150x150x8",
] as const;

export const TRUSS_WEB_PROFILE_OPTIONS = [
  "L50x50",
  "L60x60x6",
  "L70x70x7",
  "L80x80x8",
] as const;

export const PURLIN_PROFILE_OPTIONS = [
  "C150x2",
  "C200x2",
  "Z150x2",
  "Z200x2",
] as const;

export const GIRT_PROFILE_OPTIONS = ["C150x2", "C200x2", "Z150x2"] as const;

export const RAFTER_PROFILE_OPTIONS = [
  "IPE180",
  "IPE200",
  "IPE240",
  "IPE270",
] as const;

function locSuffix(ctx: SelectionContext): string {
  return ctx.locationSubtitle ? ` (${ctx.locationSubtitle})` : "";
}

function defaultScopes(
  ctx: SelectionContext,
  elementLabel: string,
): ProfileScopeOption[] {
  return [
    { scope: "selection", label: "This member" },
    {
      scope: "element_type",
      label: `All ${elementLabel.replace(/_/g, " ")}s`,
    },
    { scope: "pick_members", label: "Pick members" },
  ];
}

function frameScopes(
  ctx: SelectionContext,
  elementLabel: string,
): ProfileScopeOption[] {
  return [
    { scope: "selection", label: "This member" },
    { scope: "frame", label: `This frame (${ctx.frameMemberCount})` },
    {
      scope: "element_type",
      label: `All ${elementLabel.replace(/_/g, " ")}s`,
    },
    { scope: "pick_members", label: "Pick members" },
  ];
}

const REGISTRY: Record<ElementKind, ElementRegistryEntry> = {
  column: {
    kind: "column",
    profileCatalog: COLUMN_PROFILE_OPTIONS,
    doActions: [
      {
        id: "change_profile",
        tier: "primary",
        label: "Section size",
      },
      {
        id: "add_frame_like_this",
        tier: "primary",
        label: "Add frame like this…",
        description: "Insert a portal frame along the length",
      },
      {
        id: "switch_to_truss",
        tier: "structure",
        label: "Switch to truss frame",
      },
      {
        id: "delete_frame",
        tier: "more",
        label: "Remove frame",
        description: "Rebuilds without this frame line",
      },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Is section enough?",
        message: `Is ${ctx.profile ?? "this column"} strong enough${locSuffix(ctx)}?`,
      },
      {
        label: "Upsize options",
        message: `What larger column sections would work${locSuffix(ctx)}?`,
      },
      {
        label: "Explain this column",
        message: `Explain the role of this column${locSuffix(ctx)} in the frame.`,
      },
    ],
    profileScopes: (ctx) => frameScopes(ctx, "column"),
  },

  rafter: {
    kind: "rafter",
    profileCatalog: RAFTER_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
      {
        id: "switch_to_truss",
        tier: "structure",
        label: "Switch to truss frame",
      },
      {
        id: "delete_frame",
        tier: "more",
        label: "Remove frame",
      },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Is section enough?",
        message: `Is ${ctx.profile ?? "this rafter"} adequate${locSuffix(ctx)}?`,
      },
      {
        label: "Explain this member",
        message: `Explain the role of this rafter${locSuffix(ctx)}.`,
      },
    ],
    profileScopes: (ctx) => frameScopes(ctx, "rafter"),
  },

  truss_chord: {
    kind: "truss_chord",
    profileCatalog: TRUSS_CHORD_PROFILE_OPTIONS,
    doActions: [
      {
        id: "change_truss_type",
        tier: "primary",
        label: "Change truss type",
      },
      { id: "change_profile", tier: "primary", label: "Section size" },
      {
        id: "switch_to_rafter",
        tier: "structure",
        label: "Switch to rafter frame",
      },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Truss type advice",
        message: `Would a different truss type suit this frame${locSuffix(ctx)}?`,
      },
      {
        label: "Chord sizes",
        message: `Are the truss chord sizes balanced${locSuffix(ctx)}?`,
      },
    ],
    profileScopes: (ctx) => [
      { scope: "truss", label: `This truss (${ctx.trussMemberCount})` },
      { scope: "element_type", label: "All truss chords" },
      { scope: "pick_members", label: "Pick members" },
    ],
  },

  truss_web: {
    kind: "truss_web",
    profileCatalog: TRUSS_WEB_PROFILE_OPTIONS,
    doActions: [
      {
        id: "change_truss_type",
        tier: "primary",
        label: "Change truss type",
      },
      { id: "change_profile", tier: "primary", label: "Section size" },
      {
        id: "switch_to_rafter",
        tier: "structure",
        label: "Switch to rafter frame",
      },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Web sizes",
        message: `Are the truss web sizes balanced${locSuffix(ctx)}?`,
      },
      {
        label: "Truss type advice",
        message: `Would a different truss pattern suit this frame${locSuffix(ctx)}?`,
      },
    ],
    profileScopes: (ctx) => [
      { scope: "truss", label: `This truss (${ctx.trussMemberCount})` },
      { scope: "element_type", label: "All truss webs" },
      { scope: "pick_members", label: "Pick members" },
    ],
  },

  purlin: {
    kind: "purlin",
    profileCatalog: PURLIN_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
    ],
    advicePrompts: () => [
      {
        label: "Purlin spacing",
        message: "Is the current purlin spacing reasonable for this roof?",
      },
      {
        label: "Heavier purlins",
        message: "Suggest a heavier purlin section for this span.",
      },
    ],
    profileScopes: (ctx) => [
      { scope: "element_type", label: "All purlins" },
      { scope: "pick_members", label: "Pick members" },
    ],
  },

  wall_girt: {
    kind: "wall_girt",
    profileCatalog: GIRT_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
    ],
    advicePrompts: () => [
      {
        label: "Girt spacing",
        message: "Is wall girt spacing OK for cladding support?",
      },
      {
        label: "Heavier girts",
        message: "Suggest a heavier girt section for this wall.",
      },
    ],
    profileScopes: () => [
      { scope: "element_type", label: "All wall girts" },
      { scope: "pick_members", label: "Pick members" },
    ],
  },

  bracing: {
    kind: "bracing",
    profileCatalog: BRACING_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
      { id: "add_brace_here", tier: "primary", label: "Add brace…" },
      { id: "add_x_brace", tier: "structure", label: "Add X-brace…" },
      { id: "delete_pair", tier: "more", label: "Remove brace" },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Is this size OK?",
        message: `Is ${ctx.profile ?? "this bracing section"} adequate${locSuffix(ctx)}?`,
      },
      {
        label: "Where to brace",
        message: "Where else should I add bracing on this building?",
      },
    ],
    profileScopes: (ctx) => {
      const opts: ProfileScopeOption[] = [
        { scope: "selection", label: "This member" },
      ];
      if (ctx.pairId) {
        opts.push({ scope: "pair", label: "This X pair" });
      }
      if (ctx.groupCount > 1) {
        opts.push({
          scope: "group",
          label: `All ${ctx.label.toLowerCase()} (${ctx.groupCount})`,
        });
      }
      opts.push({ scope: "pick_members", label: "Pick members" });
      return opts;
    },
  },

  tie_beam: {
    kind: "tie_beam",
    profileCatalog: RAFTER_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Explain tie beam",
        message: `What does this tie beam do${locSuffix(ctx)}?`,
      },
    ],
    profileScopes: (ctx) => defaultScopes(ctx, "tie beam"),
  },

  generic: {
    kind: "generic",
    profileCatalog: BRACING_PROFILE_OPTIONS,
    doActions: [
      { id: "change_profile", tier: "primary", label: "Section size" },
      { id: "more_remove", tier: "more", label: "Remove member" },
    ],
    advicePrompts: (ctx) => [
      {
        label: "Explain member",
        message: `What does this ${ctx.label.toLowerCase()} do in the structure?`,
      },
    ],
    profileScopes: (ctx) => defaultScopes(ctx, ctx.elementType),
  },
};

export function resolveElementKind(ctx: SelectionContext): ElementKind {
  if (ctx.isBracing) return "bracing";
  switch (ctx.elementType) {
    case "column":
      return "column";
    case "rafter":
      return "rafter";
    case "truss_chord":
      return "truss_chord";
    case "truss_web":
      return "truss_web";
    case "purlin":
      return "purlin";
    case "wall_girt":
      return "wall_girt";
    case "tie_beam":
      return "tie_beam";
    default:
      return "generic";
  }
}

export function getElementRegistryEntry(
  ctx: SelectionContext,
): ElementRegistryEntry {
  return REGISTRY[resolveElementKind(ctx)];
}

export function actionsForSelection(ctx: SelectionContext): SelectionAction[] {
  const entry = getElementRegistryEntry(ctx);
  let actions = entry.doActions.map((action) => ({
    ...action,
    description:
      action.id === "change_profile"
        ? (ctx.profile ?? action.description)
        : action.description,
  }));

  if (ctx.frameTrussed) {
    actions = actions.filter((a) => a.id !== "switch_to_truss");
  }

  if (ctx.frameIndex === null || ctx.frameMemberCount === 0) {
    actions = actions.filter((a) => a.id !== "delete_frame");
  }

  if (ctx.isBracing) {
    const deleteAction = actions.find((a) => a.id === "delete_pair");
    if (deleteAction) {
      deleteAction.label = ctx.pairId ? "Remove X pair" : "Remove member";
    }
  }

  return actions;
}

export function profileOptionsForContext(
  ctx: SelectionContext,
): readonly string[] {
  return getElementRegistryEntry(ctx).profileCatalog;
}

export function profileScopeOptions(
  ctx: SelectionContext,
): ProfileScopeOption[] {
  return getElementRegistryEntry(ctx).profileScopes(ctx);
}

export function suggestedAiPrompts(ctx: SelectionContext): SuggestedPrompt[] {
  return getElementRegistryEntry(ctx).advicePrompts(ctx);
}

export function actionsByTier(
  actions: SelectionAction[],
): Record<SelectionAction["tier"], SelectionAction[]> {
  const buckets: Record<SelectionAction["tier"], SelectionAction[]> = {
    primary: [],
    adjust: [],
    structure: [],
    more: [],
  };
  for (const action of actions) {
    buckets[action.tier].push(action);
  }
  return buckets;
}

export function trussTypeOptions() {
  return TRUSS_TYPE_OPTIONS;
}
