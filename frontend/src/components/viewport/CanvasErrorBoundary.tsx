"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

import { viewportTheme } from "@/lib/viewport-theme";

type CanvasErrorBoundaryProps = {
  children: ReactNode;
  onReset: () => void;
};

type CanvasErrorBoundaryState = {
  hasError: boolean;
  message: string | null;
};

/**
 * Isolates R3F/WebGL failures so the rest of the app (sidebar, generate) stays usable.
 */
export class CanvasErrorBoundary extends Component<
  CanvasErrorBoundaryProps,
  CanvasErrorBoundaryState
> {
  state: CanvasErrorBoundaryState = { hasError: false, message: null };

  static getDerivedStateFromError(error: Error): CanvasErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || "Unknown 3D rendering error",
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[Viewport3D] Canvas error boundary caught:", error, info);
  }

  private handleReset = () => {
    this.setState({ hasError: false, message: null });
    this.props.onReset();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 px-6 text-center"
          style={{ background: viewportTheme.canvas.overlay }}
        >
          <p className="text-sm font-medium text-slate-900">
            3D view stopped responding
          </p>
          <p className="max-w-sm text-xs text-muted-foreground">
            {this.state.message ??
              "Invalid geometry was skipped. Adjust shed parameters and regenerate."}
          </p>
          <button
            type="button"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            onClick={this.handleReset}
          >
            Restore 3D view
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
