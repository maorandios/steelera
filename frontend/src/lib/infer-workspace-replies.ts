import type { WorkspaceQuickRepliesPayload } from "@/types/chat";

const NUMBERED_OPTIONS_RE =
  /(\d+)[.)]\s*(?:\*\*)?([\s\S]+?)(?:\*\*)?(?=(?:,\s*or\s+|\s+or\s+)\d+[.)]|\?\s*(?:Please|$)|\n\n|Please indicate|$)/gi;

const PROFILE_RE =
  /\b(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+|UB[\d.xX/-]+|UC[\d.xX/-]+|L\d+[\dxX/-]*)\b/gi;

const PROFILE_RANGE_RE =
  /from\s+(HEA\d+|HEB\d+|IPE\d+)\s+to\s+(HEA\d+|HEB\d+|IPE\d+)/i;

const YES_NO_CUE_RE =
  /\b(would you like|do you want|should i|shall i|proceed|confirm|prefer to)\b/i;

function cleanOption(raw: string): string {
  return raw
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[,;.]+$/, "");
}

function inferNumbered(content: string): WorkspaceQuickRepliesPayload | null {
  const matches = [...content.matchAll(NUMBERED_OPTIONS_RE)];
  if (matches.length < 2 || matches.length > 4) return null;

  const options: { label: string; value: string }[] = [];
  for (const match of matches) {
    const label = cleanOption(match[2] ?? "");
    if (!label || label.length > 140) return null;
    options.push({ label, value: label });
  }

  const firstIndex = matches[0]?.index ?? 0;
  let question = content
    .slice(0, firstIndex)
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[:\s]+$/, "");
  if (!question) question = "Choose an option:";
  return { question, options };
}

function profilePayload(
  question: string,
  options: { label: string; value: string }[],
): WorkspaceQuickRepliesPayload {
  return {
    question,
    options,
    allowCustom: true,
    customPlaceholder: "Type any section e.g. HEA380",
  };
}

function inferProfileChoices(content: string): WorkspaceQuickRepliesPayload | null {
  if (!content.includes("?") && !YES_NO_CUE_RE.test(content)) return null;

  const range = PROFILE_RANGE_RE.exec(content);
  if (range) {
    const low = range[1].toUpperCase();
    const high = range[2].toUpperCase();
    let question = content.trim();
    if (question.length > 220) {
      const idx = question.lastIndexOf("?");
      question = idx >= 0 ? question.slice(0, idx + 1) : question;
    }
    return profilePayload(question, [
      { label: low, value: `Yes, switch to ${low}` },
      { label: high, value: `Yes, switch to ${high}` },
      { label: "Keep current", value: "No, keep the current section" },
    ]);
  }

  const profiles = [...content.matchAll(PROFILE_RE)].map((m) =>
    (m[1] ?? "").toUpperCase(),
  );
  const unique = [...new Set(profiles)];
  if (unique.length < 2) return null;

  const currentMatch = content.match(
    /current(?:\s+\w+){0,3}\s+section\s+is\s+(HEA\d+|HEB\d+|IPE\d+)/i,
  );
  const current = currentMatch?.[1]?.toUpperCase() ?? null;
  const suggested = unique.filter((p) => p !== current);
  if (suggested.length === 0) return null;

  const options = suggested.slice(0, 3).map((p) => ({
    label: p,
    value: `Yes, switch to ${p}`,
  }));
  if (current) {
    options.push({ label: "Keep current", value: "No, keep the current section" });
  } else if (options.length < 4) {
    options.push({ label: "No", value: "No" });
  }

  let question = content.trim();
  if (question.length > 220) {
    const idx = question.lastIndexOf("?");
    question = idx >= 0 ? question.slice(0, idx + 1) : question;
  }
  return profilePayload(question, options.slice(0, 4));
}

function inferYesNo(content: string): WorkspaceQuickRepliesPayload | null {
  const text = content.trim();
  if (!text.includes("?") && !YES_NO_CUE_RE.test(text)) return null;
  if (!YES_NO_CUE_RE.test(text)) return null;

  let question = text;
  if (question.length > 240) {
    const parts = text.split(/(?<=[.!?])\s+/).filter(Boolean);
    for (let i = parts.length - 1; i >= 0; i -= 1) {
      if (parts[i].includes("?") || YES_NO_CUE_RE.test(parts[i])) {
        question = parts[i];
        break;
      }
    }
  }

  return {
    question,
    options: [
      { label: "Yes", value: "Yes" },
      { label: "No", value: "No" },
    ],
  };
}

/** Mirror backend clarification_parse — chips for AI questions. */
export function inferWorkspaceQuickReplies(
  content: string,
): WorkspaceQuickRepliesPayload | null {
  if (!content || content.length > 2500) return null;
  return (
    inferNumbered(content) ??
    inferProfileChoices(content) ??
    inferYesNo(content)
  );
}
