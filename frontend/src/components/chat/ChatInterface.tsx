"use client";

import { Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatStatus } from "@/components/chat/ChatStatus";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useProjectStore } from "@/store/project-store";

export function ChatInterface() {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const messages = useProjectStore((s) => s.messages);
  const statuses = useProjectStore((s) => s.statuses);
  const isLoading = useProjectStore((s) => s.isLoading);
  const sendMessage = useProjectStore((s) => s.sendMessage);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, statuses, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value) return;
    setInput("");
    await sendMessage(value);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ScrollArea className="min-h-0 flex-1 px-3">
        <div className="flex flex-col gap-3 py-3">
          {messages.map((msg, i) => (
            <ChatMessage key={`${msg.role}-${i}-${msg.content.slice(0, 12)}`} message={msg} />
          ))}
          <ChatStatus statuses={statuses} isLoading={isLoading} />
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <form
        onSubmit={handleSubmit}
        suppressHydrationWarning
        className="sticky bottom-0 z-10 border-t border-border bg-background/95 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-md"
      >
        <div className="flex gap-2" suppressHydrationWarning>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your structure..."
            disabled={isLoading}
            className="flex-1 bg-card"
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
