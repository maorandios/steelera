"use client";

import { Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatStatus } from "@/components/chat/ChatStatus";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";

type ChatInterfaceProps = {
  variant?: "desktop" | "default";
};

export function ChatInterface({ variant = "default" }: ChatInterfaceProps) {
  const isDesktop = variant === "desktop";
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const messages = useProjectStore((s) => s.messages);
  const statuses = useProjectStore((s) => s.statuses);
  const isLoading = useProjectStore((s) => s.isLoading);
  const sendMessage = useProjectStore((s) => s.sendMessage);
  const selectedElementId = useProjectStore((s) => s.selectedElementId);
  const clearSelection = useProjectStore((s) => s.clearSelection);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, statuses, isLoading, scrollToBottom]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value) return;
    setInput("");
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
            />
          ))}
          <ChatStatus statuses={statuses} isLoading={isLoading} />
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        suppressHydrationWarning
        className={cn(
          "shrink-0 border-t border-border bg-background",
          isDesktop
            ? "p-5 pb-5"
            : "p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]",
        )}
      >
        {selectedElementId ? (
          <div className="mb-2">
            <Badge
              variant="secondary"
              className="gap-1.5 pr-1 font-normal"
            >
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
        <div className="flex gap-2" suppressHydrationWarning>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your structure..."
            disabled={isLoading}
            className={cn(
              "flex-1 bg-card",
              isDesktop && "h-11 text-base",
            )}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore
            data-form-type="other"
            suppressHydrationWarning
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
            <span className="sr-only">Send</span>
          </Button>
        </div>
      </form>
    </div>
  );
}
