"use client";

import { ArrowUp, Send, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatStatus } from "@/components/chat/ChatStatus";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

type ChatInterfaceProps = {
  variant?: "desktop" | "default" | "onboarding";
};

function findActiveActionMessageIndex(messages: ChatMessageType[]): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    const block = message.ui_block;
    if (
      message.role === "assistant" &&
      (block?.type === "quick_replies" ||
        block?.type === "show_proposal" ||
        block?.type === "location_picker" ||
        block?.type === "site_refine" ||
        block?.type === "map_pin_picker")
    ) {
      return i;
    }
  }
  return -1;
}

function customInputPlaceholder(
  messages: ChatMessageType[],
  awaitingCustom: string | null,
): string {
  if (!awaitingCustom) return "Type your answer…";
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const block = messages[i].ui_block;
    if (
      block?.type === "quick_replies" &&
      block.payload.onboardingPhase === awaitingCustom
    ) {
      const unit = block.payload.customUnit;
      const hint = block.payload.customPlaceholder;
      if (awaitingCustom === "use_case") return "Describe your use case…";
      if (unit === "m" && hint) return `${hint} (metres)`;
      return hint ?? "Type your answer…";
    }
  }
  if (awaitingCustom === "location") return "City or street address…";
  if (awaitingCustom === "use_case") return "Describe your use case…";
  return "Type your answer…";
}

export function ChatInterface({ variant = "default" }: ChatInterfaceProps) {
  const isDesktop = variant === "desktop";
  const isOnboarding = variant === "onboarding";
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const messages = useProjectStore((s) => s.messages);
  const statuses = useProjectStore((s) => s.statuses);
  const isLoading = useProjectStore((s) => s.isLoading);
  const isProposing = useProjectStore((s) => s.isProposing);
  const sendMessage = useProjectStore((s) => s.sendMessage);
  const submitOnboardingCustom = useProjectStore((s) => s.submitOnboardingCustom);
  const onboardingAwaitingCustom = useProjectStore((s) => s.onboardingAwaitingCustom);
  const error = useProjectStore((s) => s.error);
  const clearError = useProjectStore((s) => s.clearError);
  const selectedElementId = useProjectStore((s) => s.selectedElementId);
  const clearSelection = useProjectStore((s) => s.clearSelection);

  const activeActionIndex = useMemo(
    () => findActiveActionMessageIndex(messages),
    [messages],
  );
  const showInput = !isOnboarding || onboardingAwaitingCustom !== null;
  const inputPlaceholder = customInputPlaceholder(messages, onboardingAwaitingCustom);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, statuses, isLoading, isProposing, scrollToBottom]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value) return;
    setInput("");
    if (isOnboarding && onboardingAwaitingCustom) {
      await submitOnboardingCustom(value);
      return;
    }
    await sendMessage(value);
  };

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div
        ref={scrollRef}
        className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-y-contain px-3"
        aria-label="Chat messages"
      >
        <div className="mt-auto flex shrink-0 flex-col gap-3 py-3">
          {messages.map((msg, i) => (
            <ChatMessage
              key={`${msg.role}-${i}-${msg.content.slice(0, 12)}`}
              message={msg}
              actionsActive={i === activeActionIndex}
              variant={isOnboarding ? "onboarding" : "default"}
            />
          ))}
          <ChatStatus
            statuses={statuses}
            isLoading={isLoading || isProposing}
          />
        </div>
      </div>

      {showInput ? (
        <form
          onSubmit={handleSubmit}
          suppressHydrationWarning
          className={cn(
            "shrink-0",
            isDesktop
              ? "border-t border-border bg-background p-5 pb-5"
              : isOnboarding
                ? "px-1 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2"
                : "border-t border-border bg-background p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]",
          )}
        >
          {selectedElementId ? (
            <div className="mb-2">
              <Badge variant="secondary" className="gap-1.5 pr-1 font-normal">
                <span>Member: {selectedElementId}</span>
                <button
                  type="button"
                  onClick={clearSelection}
                  className="rounded-sm p-0.5 hover:bg-muted-foreground/20"
                  aria-label="Clear selection"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            </div>
          ) : null}
          {isOnboarding && error ? (
            <p className="mb-2 text-center text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
          <div
            className={cn(
              "flex gap-2",
              isOnboarding &&
                "items-center rounded-full border border-white/70 bg-white/75 px-3 py-2 shadow-[0_8px_32px_rgba(15,23,42,0.08)] backdrop-blur-xl sm:px-4",
            )}
            suppressHydrationWarning
          >
            {isOnboarding ? (
              <input
                value={input}
                onChange={(e) => {
                  if (error) clearError();
                  setInput(e.target.value);
                }}
                placeholder={inputPlaceholder}
                disabled={isLoading || isProposing}
                className="min-w-0 flex-1 bg-transparent text-base text-slate-800 placeholder:text-slate-400 focus:outline-none"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore
                data-form-type="other"
                suppressHydrationWarning
              />
            ) : (
              <Input
                value={input}
                onChange={(e) => {
                  if (error) clearError();
                  setInput(e.target.value);
                }}
                placeholder={
                  isOnboarding
                    ? inputPlaceholder
                    : "Describe your structure..."
                }
                disabled={isLoading || isProposing}
                className={cn(
                  "flex-1 bg-card",
                  (isDesktop || isOnboarding) && "h-11 text-base",
                )}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore
                data-form-type="other"
                suppressHydrationWarning
              />
            )}
            {isOnboarding ? (
              <button
                type="submit"
                disabled={isLoading || isProposing || !input.trim()}
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                  "bg-blue-600 text-white shadow-md transition-all",
                  "hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none",
                )}
                aria-label="Send"
              >
                <ArrowUp className="h-5 w-5" />
              </button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={isLoading || isProposing || !input.trim()}
                className={isOnboarding ? "h-11 w-11" : undefined}
              >
                <Send className="h-4 w-4" />
                <span className="sr-only">Send</span>
              </Button>
            )}
          </div>
        </form>
      ) : (
        <p className="shrink-0 px-4 py-3 text-center text-xs text-slate-400">
          Tap an option above to continue
        </p>
      )}
    </div>
  );
}
