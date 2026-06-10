import type { ChatMessage } from "@/types/chat";

const APPLY_QUESTION_RE =
  /Apply\s+(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)\s+to which/i;
const SWITCH_RE =
  /(?:yes,?\s*)?switch to\s+(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)/i;
const PLAIN_PROFILE_RE =
  /^(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)$/i;

/** Last profile the user chose in the chat thread (for pick-on-model). */
export function extractPendingProfileFromMessages(
  messages: ChatMessage[],
): string | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (msg.role === "assistant") {
      const applyMatch = APPLY_QUESTION_RE.exec(msg.content);
      if (applyMatch?.[1]) return applyMatch[1].toUpperCase();
    }
    if (msg.role === "user") {
      const switchMatch = SWITCH_RE.exec(msg.content);
      if (switchMatch?.[1]) return switchMatch[1].toUpperCase();
      const plainMatch = PLAIN_PROFILE_RE.exec(msg.content.trim());
      if (plainMatch?.[1]) return plainMatch[1].toUpperCase();
      const applyUser = msg.content.match(
        /^Apply\s+(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)\s+to/i,
      );
      if (applyUser?.[1]) return applyUser[1].toUpperCase();
    }
  }
  return null;
}

export const WORKSPACE_CUSTOM_PROFILE = "__custom_profile__";
export const WORKSPACE_PICK_ON_MODEL = "__pick_on_model__";

export function profileChoiceMessage(profile: string): string {
  return `Yes, switch to ${profile.toUpperCase()}`;
}
