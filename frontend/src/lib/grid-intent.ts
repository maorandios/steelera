/** Parse structural grid toggles from chat prompts (mirrors backend grid_intent.py). */

import type { ShedRoofStyle } from "@/lib/shed-assembly";
import type { TrussType } from "@/types/shed-config";
import type { GridDefinition } from "@/types/spatial-grid";

const TRUSS_TYPE_PATTERNS: ReadonlyArray<[Exclude<TrussType, "none">, RegExp]> = [
  ["scissor", /scissor/i],
  ["queen_post", /queen[\s-]?post/i],
  ["king_post", /king[\s-]?post/i],
  ["fink", /\bfink\b/i],
  ["warren", /\bwarren\b/i],
  ["howe", /\bhowe\b/i],
  ["pratt", /\bpratt\b/i],
];

const BOOL_FIELDS = new Set([
  "use_truss",
  "x_bracing",
  "gable_bracing",
  "roof_bracing",
  "sag_rods",
  "haunches",
  "fly_braces",
  "base_plates",
  "bottom_chord_restraint",
  "generate_wall_girts",
  "generate_purlins",
  "generate_tie_beams",
] as const);

const FEATURE_ALIASES: ReadonlyArray<
  [keyof GridIntentOverrides, readonly string[]]
> = [
  ["generate_purlins", ["roof purlin", "purlin", "purlins"]],
  ["generate_wall_girts", ["wall girt", "girts", "girt"]],
  [
    "roof_bracing",
    [
      "roof cross-bracing",
      "roof cross bracing",
      "roof x-bracing",
      "roof x bracing",
      "roof bracing",
    ],
  ],
  [
    "x_bracing",
    [
      "wall cross-bracing",
      "wall cross bracing",
      "side wall bracing",
      "long wall bracing",
      "wall x-bracing",
      "wall x bracing",
      "wall bracing",
      "x-bracing",
      "x bracing",
    ],
  ],
  ["gable_bracing", ["gable bracing", "end wall bracing", "gable x-bracing"]],
  ["sag_rods", ["sag rod", "sag rods", "anti-sag"]],
  ["use_truss", ["truss", "trusses"]],
  ["bottom_chord_restraint", ["bottom chord restraint", "bc restraint"]],
  ["base_plates", ["base plate", "base plates"]],
  ["fly_braces", ["fly brace", "fly braces", "flange brace"]],
  ["haunches", ["haunch", "haunches"]],
  ["generate_tie_beams", ["tie beam", "tie beams", "longitudinal tie"]],
];

const DISABLED_RE =
  /\b(?:disabled|disable|off|no|none|zero|0|do\s+not\s+generate|don't\s+generate|without)\b/i;
const ENABLED_RE =
  /\b(?:enabled|enable|on|yes|generate|include|with)\b/i;

export interface GridIntentOverrides {
  use_truss?: boolean;
  truss_type?: Exclude<TrussType, "none">;
  roof_style?: ShedRoofStyle;
  roof_pitch_deg?: number;
  x_bracing?: boolean;
  gable_bracing?: boolean;
  roof_bracing?: boolean;
  sag_rods?: boolean;
  haunches?: boolean;
  fly_braces?: boolean;
  base_plates?: boolean;
  bottom_chord_restraint?: boolean;
  generate_purlins?: boolean;
  generate_wall_girts?: boolean;
  generate_tie_beams?: boolean;
}

function lineForMatch(text: string, start: number): string {
  const lineStart = text.lastIndexOf("\n", start) + 1;
  const lineEnd = text.indexOf("\n", start);
  return text.slice(lineStart, lineEnd < 0 ? undefined : lineEnd);
}

function featureTristateFromText(
  text: string,
  aliases: readonly string[],
): boolean | undefined {
  if (!text.trim()) return undefined;

  const lower = text.toLowerCase();
  for (const alias of aliases) {
    const pattern = new RegExp(`\\b${alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(lower)) !== null) {
      const line = lineForMatch(lower, match.index);
      if (DISABLED_RE.test(line)) return false;
      if (ENABLED_RE.test(line)) return true;
    }
  }
  return undefined;
}

export function extractGridIntentFromText(text: string): GridIntentOverrides {
  if (!text.trim()) return {};

  const t = text.toLowerCase();
  const intent: GridIntentOverrides = {};

  if (/\bmono[\s-]?pitch\b|\bmonopitch\b|single[\s-]slope|\bmono[\s-]shed\b/.test(t)) {
    intent.roof_style = "mono_pitch";
  } else if (/\bflat[\s-]?roof\b|\bflat[\s-]?pitch\b/.test(t)) {
    intent.roof_style = "flat";
  } else if (/\bduo[\s-]?pitch\b|\bduopitch\b|\bgable[\s-]?roof\b/.test(t)) {
    intent.roof_style = "duo_pitch";
  }

  if (/\btruss(?:es)?\b/.test(t)) {
    const trussState = featureTristateFromText(text, ["truss", "trusses"]);
    if (trussState !== false) {
      intent.use_truss = true;
    }
  }

  for (const [trussType, pattern] of TRUSS_TYPE_PATTERNS) {
    if (pattern.test(text)) {
      intent.use_truss = true;
      intent.truss_type = trussType;
      break;
    }
  }

  for (const [field, aliases] of FEATURE_ALIASES) {
    const state = featureTristateFromText(text, aliases);
    if (state !== undefined) {
      intent[field] = state;
    }
  }

  if (intent.x_bracing === undefined && intent.roof_bracing === undefined) {
    if (
      /\bbracing\b/i.test(text) &&
      !/roof[\s-]?(?:cross[\s-]?)?bracing|gable[\s-]?bracing|wall[\s-]?(?:cross[\s-]?)?bracing/i.test(
        text,
      )
    ) {
      intent.x_bracing = true;
    }
  }

  const pitchMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:°|deg(?:ree)?s?|pitch)/i);
  if (pitchMatch) {
    intent.roof_pitch_deg = Number(pitchMatch[1]);
  }

  return intent;
}

export function extractGridIntentFromMessages(
  messages: { role: string; content: string }[],
): GridIntentOverrides {
  const merged: GridIntentOverrides = {};
  for (const message of messages) {
    if (message.role !== "user") continue;
    Object.assign(merged, extractGridIntentFromText(message.content));
  }
  return merged;
}

export function mergeGridDefinitionWithIntent(
  gd: GridDefinition,
  intent: GridIntentOverrides,
  options?: { fillGapsOnly?: boolean },
): GridDefinition {
  if (Object.keys(intent).length === 0) return gd;

  const fillGapsOnly = options?.fillGapsOnly ?? true;
  const useTruss = Boolean(intent.use_truss ?? gd.use_truss);
  const trussType =
    intent.truss_type ??
    (gd.truss_type && gd.truss_type !== "none" ? gd.truss_type : "pratt");

  const merged: GridDefinition = {
    ...gd,
    roof_style: intent.roof_style ?? gd.roof_style,
    roof_pitch_deg: intent.roof_pitch_deg ?? gd.roof_pitch_deg,
    use_truss: useTruss,
    truss_type: useTruss ? trussType : "none",
  };

  if (!fillGapsOnly) {
    for (const key of BOOL_FIELDS) {
      const value = intent[key as keyof GridIntentOverrides];
      if (typeof value === "boolean") {
        (merged as Record<string, boolean>)[key] = value;
      }
    }
    return merged;
  }

  return {
    ...merged,
    x_bracing: intent.x_bracing ?? gd.x_bracing ?? false,
    gable_bracing: intent.gable_bracing ?? gd.gable_bracing ?? false,
    roof_bracing: intent.roof_bracing ?? gd.roof_bracing ?? false,
    sag_rods: intent.sag_rods ?? gd.sag_rods ?? false,
    haunches: intent.haunches ?? gd.haunches ?? false,
    fly_braces: intent.fly_braces ?? gd.fly_braces ?? false,
    base_plates: intent.base_plates ?? gd.base_plates ?? false,
    bottom_chord_restraint:
      intent.bottom_chord_restraint ?? gd.bottom_chord_restraint ?? false,
    generate_purlins: intent.generate_purlins ?? gd.generate_purlins ?? true,
    generate_wall_girts:
      intent.generate_wall_girts ?? gd.generate_wall_girts ?? true,
    generate_tie_beams: intent.generate_tie_beams ?? gd.generate_tie_beams ?? true,
  };
}
