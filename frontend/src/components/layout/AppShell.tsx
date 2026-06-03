"use client";

import { Maximize2, Minimize2 } from "lucide-react";

import { ChatInterface } from "@/components/chat/ChatInterface";
import { Viewport3D } from "@/components/viewport/Viewport3D";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useProjectStore } from "@/store/project-store";

export function AppShell() {
  const viewportExpanded = useProjectStore((s) => s.viewportExpanded);
  const toggleViewport = useProjectStore((s) => s.toggleViewport);

  return (
    <div
      className="grid h-dvh w-full grid-rows-[minmax(0,1fr)_minmax(0,1fr)] overflow-hidden bg-background md:grid-rows-1 md:grid-cols-[1.1fr_0.9fr]"
      style={{
        gridTemplateRows: viewportExpanded
          ? "minmax(0,2fr) minmax(0,1fr)"
          : undefined,
      }}
    >
      <section className="relative flex min-h-0 flex-col p-3 pb-0 md:p-4 md:pr-2">
        <header className="mb-2 flex items-center justify-between gap-2">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">
              Steelera
            </h1>
            <p className="text-xs text-muted-foreground">
              Structural steel design
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="md:hidden"
            onClick={toggleViewport}
            aria-label={viewportExpanded ? "Shrink viewport" : "Expand viewport"}
          >
            {viewportExpanded ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        </header>
        <div className="min-h-0 flex-1">
          <Viewport3D />
        </div>
      </section>

      <Separator className="md:hidden" />

      <section className="flex min-h-0 flex-col border-border md:border-l md:pl-0">
        <ChatInterface />
      </section>
    </div>
  );
}
