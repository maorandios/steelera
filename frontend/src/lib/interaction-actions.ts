import type {
  ProfileScope,
  SelectionAction,
  SelectionContext,
} from "@/types/interaction";
import { TRUSS_TYPE_OPTIONS } from "@/types/shed-config";

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

export const RAFTER_PROFILE_OPTIONS = ["IPE180", "IPE200", "IPE240", "IPE270"] as const;

export function profileOptionsForContext(ctx: SelectionContext): readonly string[] {
  if (ctx.isBracing) return BRACING_PROFILE_OPTIONS;
  switch (ctx.elementType) {
    case "column":
      return COLUMN_PROFILE_OPTIONS;
    case "truss_chord":
      return TRUSS_CHORD_PROFILE_OPTIONS;
    case "truss_web":
      return TRUSS_WEB_PROFILE_OPTIONS;
    case "purlin":
      return PURLIN_PROFILE_OPTIONS;
    case "wall_girt":
      return GIRT_PROFILE_OPTIONS;
    case "rafter":
      return RAFTER_PROFILE_OPTIONS;
    default:
      return BRACING_PROFILE_OPTIONS;
  }
}

export type ProfileScopeOption = {
  scope: ProfileScope;
  label: string;
};

export function profileScopeOptions(ctx: SelectionContext): ProfileScopeOption[] {
  if (ctx.isBracing) {
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
    return opts;
  }

  const opts: ProfileScopeOption[] = [];

  if (ctx.parentAssembly === "truss") {
    opts.push(
      { scope: "truss", label: `This truss (${ctx.trussMemberCount})` },
      { scope: "element_type", label: "All truss chords" },
    );
    if (ctx.elementType === "truss_web") {
      return [
        { scope: "truss", label: `This truss (${ctx.trussMemberCount})` },
        { scope: "element_type", label: "All truss webs" },
      ];
    }
    return opts;
  }

  if (ctx.parentAssembly === "frame") {
    opts.push(
      { scope: "frame", label: `This frame (${ctx.frameMemberCount})` },
      { scope: "element_type", label: `All ${ctx.elementType.replace(/_/g, " ")}s` },
    );
    return opts;
  }

  if (ctx.parentAssembly === "purlin_run" || ctx.parentAssembly === "girt_run") {
    return [{ scope: "element_type", label: `All ${ctx.label.toLowerCase()}s` }];
  }

  return [
    { scope: "selection", label: "This member" },
    { scope: "element_type", label: `All ${ctx.elementType.replace(/_/g, " ")}s` },
  ];
}

export function actionsForSelection(ctx: SelectionContext): SelectionAction[] {
  const actions: SelectionAction[] = [];

  if (ctx.isBracing) {
    actions.push(
      {
        id: "change_profile",
        tier: "primary",
        label: "Section size",
        description: ctx.profile ?? undefined,
      },
      { id: "add_brace_here", tier: "primary", label: "Add brace…" },
      { id: "add_x_brace", tier: "structure", label: "Add X-brace…" },
      {
        id: "delete_pair",
        tier: "more",
        label: ctx.pairId ? "Remove X pair" : "Remove member",
      },
    );
    return actions;
  }

  switch (ctx.parentAssembly) {
    case "truss":
      actions.push(
        {
          id: "change_truss_type",
          tier: "primary",
          label: "Change truss type",
          description: ctx.trussType ?? "Pick pattern",
        },
        {
          id: "change_profile",
          tier: "primary",
          label: "Section size",
          description: ctx.profile ?? undefined,
        },
      );
      if (ctx.frameIndex !== null) {
        actions.push({
          id: "switch_to_rafter",
          tier: "structure",
          label: "Switch to rafter frame",
        });
      }
      break;

    case "frame":
      if (ctx.elementType === "column") {
        actions.push(
          {
            id: "change_profile",
            tier: "primary",
            label: "Section size",
            description: ctx.profile ?? undefined,
          },
          {
            id: "add_frame_like_this",
            tier: "primary",
            label: "Add frame like this…",
            description: "Insert a portal frame along the length",
          },
        );
        if (!ctx.frameTrussed) {
          actions.push({
            id: "switch_to_truss",
            tier: "structure",
            label: "Switch to truss frame",
          });
        }
      } else if (ctx.elementType === "rafter") {
        actions.push(
          {
            id: "change_profile",
            tier: "primary",
            label: "Section size",
            description: ctx.profile ?? undefined,
          },
          {
            id: "switch_to_truss",
            tier: "structure",
            label: "Switch to truss frame",
          },
        );
      } else {
        actions.push({
          id: "change_profile",
          tier: "primary",
          label: "Section size",
          description: ctx.profile ?? undefined,
        });
      }
      if (ctx.frameIndex !== null && ctx.frameMemberCount > 0) {
        actions.push({
          id: "delete_frame",
          tier: "more",
          label: "Remove frame",
          description: "Rebuilds without this frame line",
        });
      }
      break;

    case "purlin_run":
    case "girt_run":
      actions.push({
        id: "change_profile",
        tier: "primary",
        label: "Section size",
        description: ctx.profile ?? undefined,
      });
      break;

    default:
      actions.push({
        id: "change_profile",
        tier: "primary",
        label: "Section size",
        description: ctx.profile ?? undefined,
      });
      actions.push({
        id: "more_remove",
        tier: "more",
        label: "Remove member",
      });
      break;
  }

  return actions;
}

export function trussTypeOptions() {
  return TRUSS_TYPE_OPTIONS;
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
