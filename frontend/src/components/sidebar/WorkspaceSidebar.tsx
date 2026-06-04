"use client";

import { useEffect, useState } from "react";

import { ElementPropertiesPanel } from "@/components/sidebar/ElementPropertiesPanel";
import { ProjectPresetsPanel } from "@/components/sidebar/ProjectPresetsPanel";
import { ClientOnly } from "@/components/ui/client-only";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useProjectStore } from "@/store/project-store";

type SidebarTab = "project" | "properties";

export function WorkspaceSidebar() {
  const selectedElementId = useProjectStore((s) => s.selectedElementId);
  const [activeTab, setActiveTab] = useState<SidebarTab>("project");

  useEffect(() => {
    if (selectedElementId) {
      setActiveTab("properties");
    }
  }, [selectedElementId]);

  return (
    <aside className="flex min-h-0 min-w-0 flex-col border-l border-border bg-background">
      <header className="shrink-0 border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight">Workspace</h2>
        <p className="text-xs text-muted-foreground">Project &amp; selection</p>
      </header>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as SidebarTab)}
        className="flex min-h-0 flex-1 flex-col px-3 pt-3"
      >
        <TabsList className="w-full">
          <TabsTrigger value="project" className="text-[11px]">
            Project &amp; Presets
          </TabsTrigger>
          <TabsTrigger value="properties" className="text-[11px]">
            Element Properties
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="min-h-0 flex-1 pb-4">
          <TabsContent value="project" className="px-1 pb-4">
            <ClientOnly
              fallback={
                <div
                  className="min-h-[280px] animate-pulse rounded-lg bg-muted/30"
                  aria-hidden
                />
              }
            >
              <ProjectPresetsPanel />
            </ClientOnly>
          </TabsContent>
          <TabsContent value="properties" className="px-1 pb-4">
            <ClientOnly
              fallback={
                <div
                  className="min-h-[200px] animate-pulse rounded-lg bg-muted/30"
                  aria-hidden
                />
              }
            >
              <ElementPropertiesPanel />
            </ClientOnly>
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </aside>
  );
}
