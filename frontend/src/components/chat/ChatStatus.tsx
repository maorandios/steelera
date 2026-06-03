"use client";

import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";

interface ChatStatusProps {
  statuses: string[];
  isLoading: boolean;
}

export function ChatStatus({ statuses, isLoading }: ChatStatusProps) {
  if (!isLoading && statuses.length === 0) return null;

  const latest = statuses[statuses.length - 1];

  return (
    <div className="flex flex-wrap items-center gap-2 px-1 py-2">
      {isLoading && (
        <Loader2 className="h-3.5 w-3.5 animate-spin text-accent-foreground" />
      )}
      {latest && (
        <Badge
          variant="secondary"
          className="border border-border bg-secondary/80 font-normal text-accent-foreground"
        >
          {latest}
        </Badge>
      )}
    </div>
  );
}
