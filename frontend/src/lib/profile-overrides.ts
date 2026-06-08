/** Parse catalog profile fields from chat / checklist prompts (mirrors backend). */

const PROFILE_FIELDS = [
  "column_profile",
  "bracing_profile",
  "purlin_profile",
  "girt_profile",
  "sag_rod_profile",
  "base_plate_profile",
  "truss_chord_profile",
  "truss_web_profile",
] as const;

export type ProfileField = (typeof PROFILE_FIELDS)[number];
export type ProfileOverrides = Partial<Record<ProfileField, string>>;

const TRUSS_PROFILE_PATTERNS: ReadonlyArray<[ProfileField, RegExp]> = [
  [
    "truss_chord_profile",
    /(?:truss\s+chords?(?:\s*\([^)]*\))?|(?:top|bottom)\s+chords?|tc\s*(?:&|and)\s*bc)\s*[-:=]\s*([A-Za-z][A-Za-z0-9xX.\-/]+)/i,
  ],
  [
    "truss_web_profile",
    /(?:truss\s+web(?:\s+diagonals?)?|web\s+diagonals?)\s*[-:=]\s*([A-Za-z][A-Za-z0-9xX.\-/]+)/i,
  ],
];

function fieldPattern(field: ProfileField): RegExp {
  const alias = field.replace(/_/g, "[_\\s]");
  const role = field.split("_")[0];
  return new RegExp(
    `(?:${alias}|${role}\\s+profile)\\s*[:=]?\\s*([A-Za-z][A-Za-z0-9xX.\\-/]+)`,
    "i",
  );
}

export function extractProfilesFromText(text: string): ProfileOverrides {
  if (!text.trim()) return {};

  const found: ProfileOverrides = {};
  for (const [field, pattern] of TRUSS_PROFILE_PATTERNS) {
    const match = pattern.exec(text);
    if (!match) continue;
    const value = match[1].trim().replace(/[.,;]+$/, "");
    if (value) found[field] = value;
  }
  for (const field of PROFILE_FIELDS) {
    const match = fieldPattern(field).exec(text);
    if (!match) continue;
    const value = match[1].trim().replace(/[.,;]+$/, "");
    if (value) found[field] = value;
  }
  return found;
}

export function extractProfilesFromMessages(
  messages: { role: string; content: string }[],
): ProfileOverrides {
  const merged: ProfileOverrides = {};
  for (const message of messages) {
    if (message.role !== "user") continue;
    Object.assign(merged, extractProfilesFromText(message.content));
  }
  return merged;
}
