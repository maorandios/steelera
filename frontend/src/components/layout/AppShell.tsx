"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";
import { WorkspaceSidebar } from "@/components/sidebar/WorkspaceSidebar";
import { Viewport3D } from "@/components/viewport/Viewport3D";

export function AppShell() {
  return (
    <div className="grid h-dvh w-full grid-cols-[25vw_55vw_20vw] overflow-hidden bg-background">
      <section className="flex min-h-0 min-w-0 flex-col border-r border-border">
        <header className="shrink-0 border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold tracking-tight">AI Assistant</h2>
          <p className="text-xs text-muted-foreground">
            Describe macros or refine the model
          </p>
        </header>
        <div className="min-h-0 flex-1">
          <ChatInterface variant="desktop" />
        </div>
      </section>

      <section className="relative flex min-h-0 min-w-0 flex-col p-4">
        <header className="mb-3 shrink-0">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">
            Steelera
          </h1>
          <p className="text-xs text-muted-foreground">
            Structural steel design · 3D workspace
          </p>
        </header>
        <div className="relative min-h-[280px] flex-1">
          <Viewport3D />
        </div>
      </section>

      <WorkspaceSidebar />
    </div>
  );
}
