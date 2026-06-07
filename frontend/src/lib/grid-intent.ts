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
  generate_wall_girts?: boolean;
  generate_tie_beams?: boolean;
}

export function extractGridIntentFromText(text: string): GridIntentOverrides {
  if (!text.trim()) return {};

  const t = text.toLowerCase();
  const intent: GridIntentOverrides = {};

  if (/\bmono[\s-]?pitch\b|\bmonopitch\b|single[\s-]slope|\bmono[\s-]?shed\b/.test(t)) {
    intent.roof_style = "mono_pitch";
  } else if (/\bflat[\s-]?roof\b|\bflat[\s-]?pitch\b/.test(t)) {
    intent.roof_style = "flat";
  } else if (/\bduo[\s-]?pitch\b|\bduopitch\b|\bgable[\s-]?roof\b/.test(t)) {
    intent.roof_style = "duo_pitch";
  }

  if (/\btruss(?:es)?\b/.test(t) && !/\bno[\s-]?truss|\bwithout[\s-]?truss/.test(t)) {
    intent.use_truss = true;
  }

  for (const [trussType, pattern] of TRUSS_TYPE_PATTERNS) {
    if (pattern.test(text)) {
      intent.use_truss = true;
      intent.truss_type = trussType;
      break;
    }
  }

  if (/bottom[\s-]?chord[\s-]?restraint|bc[\s-]?restraint/i.test(text)) {
    intent.bottom_chord_restraint = true;
    intent.use_truss = true;
  }
  if (/\bsag[\s-]?rod/i.test(text)) intent.sag_rods = true;
  if (/\bbase[\s-]?plate/i.test(text)) intent.base_plates = true;
  if (/\bgirt/i.test(text) && !/\bno[\s-]?girt/i.test(text)) {
    intent.generate_wall_girts = true;
  }
  if (/roof[\s-]?bracing|bracing[\s-]?in[\s-]?the[\s-]?roof/i.test(text)) {
    intent.roof_bracing = true;
  }
  if (/gable[\s-]?bracing|end[\s-]?wall[\s-]?bracing/i.test(text)) {
    intent.gable_bracing = true;
  }
  if (
    /side[\s-]?bracing|wall[\s-]?bracing|long[\s-]?wall[\s-]?bracing|x[\s-]?bracing/i.test(
      text,
    ) ||
    (/\bbracing\b/i.test(text) &&
      !/roof bracing/i.test(text) &&
      !/gable bracing/i.test(text))
  ) {
    intent.x_bracing = true;
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
): GridDefinition {
  if (Object.keys(intent).length === 0) return gd;

  const useTruss = Boolean(intent.use_truss ?? gd.use_truss);
  const trussType =
    intent.truss_type ??
    (gd.truss_type && gd.truss_type !== "none" ? gd.truss_type : "pratt");

  return {
    ...gd,
    roof_style: intent.roof_style ?? gd.roof_style,
    roof_pitch_deg: intent.roof_pitch_deg ?? gd.roof_pitch_deg,
    use_truss: useTruss,
    truss_type: useTruss ? trussType : "none",
    x_bracing: intent.x_bracing ?? gd.x_bracing ?? false,
    gable_bracing: intent.gable_bracing ?? gd.gable_bracing ?? false,
    roof_bracing: intent.roof_bracing ?? gd.roof_bracing ?? false,
    sag_rods: intent.sag_rods ?? gd.sag_rods ?? false,
    haunches: intent.haunches ?? gd.haunches ?? false,
    fly_braces: intent.fly_braces ?? gd.fly_braces ?? false,
    base_plates: intent.base_plates ?? gd.base_plates ?? false,
    bottom_chord_restraint:
      intent.bottom_chord_restraint ?? gd.bottom_chord_restraint ?? false,
    generate_wall_girts:
      intent.generate_wall_girts ?? gd.generate_wall_girts ?? true,
    generate_tie_beams:
      intent.generate_tie_beams ?? gd.generate_tie_beams ?? true,
  };
}
