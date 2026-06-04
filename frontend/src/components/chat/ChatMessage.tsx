"use client";

import { ShedComponentChecklist } from "@/components/chat/ShedComponentChecklist";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const checklist =
    !isUser && message.ui_block?.type === "show_component_checklist"
      ? message.ui_block.payload
      : null;

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border bg-card text-card-foreground",
          checklist && "max-w-full w-full",
        )}
      >
        {!isUser && (
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Steelera AI
          </p>
        )}
        <p className="whitespace-pre-wrap">{message.content}</p>
        {checklist ? <ShedComponentChecklist payload={checklist} /> : null}
      </div>
    </div>
  );
}
