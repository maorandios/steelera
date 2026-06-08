/**
 * Viewport + UI theme tokens. Switch `VIEWPORT_THEME_MODE` to toggle light/dark later.
 */
export type ViewportThemeMode = "light" | "dark";

export type ViewportTheme = {
  performance: {
    /** HDR environment maps are disabled by default — they exhaust GPU VRAM on large sheds. */
    enableEnvironment: boolean;
    environmentMaxElements: number;
    enableShadows: boolean;
    maxDpr: number;
  };
  canvas: {
    background: string;
    overlay: string;
    border: string;
  };
  lighting: {
    ambient: number;
    directional: number;
    directionalPosition: [number, number, number];
    fill: number;
    fillPosition: [number, number, number];
  };
  environment: {
    preset: "studio" | "apartment" | "city" | "warehouse";
    intensity: number;
  };
  steel: {
    colors: Record<string, string>;
    default: string;
    selected: string;
    metalness: number;
    roughness: number;
  };
  grid: {
    primary: string;
    minor: string;
    labelBackground: string;
    labelBorder: string;
    labelText: string;
    labelShadow: string;
  };
  selection: {
    edge: string;
  };
  placeholder: string;
};

const lightTheme: ViewportTheme = {
  performance: {
    enableEnvironment: false,
    environmentMaxElements: 120,
    enableShadows: false,
    maxDpr: 1,
  },
  canvas: {
    background: "#f5f6f8",
    overlay: "rgba(245, 246, 248, 0.95)",
    border: "#e2e8f0",
  },
  lighting: {
    ambient: 0.72,
    directional: 1.25,
    directionalPosition: [18, 28, 14],
    fill: 0.35,
    fillPosition: [-12, 16, -10],
  },
  environment: {
    preset: "studio",
    intensity: 0.55,
  },
  steel: {
    colors: {
      "I-beam": "#8b95a5",
      "C-channel": "#7f8c8d",
      Box: "#95a5a6",
      Pipe: "#9aa8b2",
      Plate: "#a8b0ba",
      Haunch: "#7d8a96",
      RHS: "#8b959f",
      CHS: "#94a0ab",
      Angle: "#8896a3",
      Tee: "#8a96a4",
      Zed: "#7f8c8d",
    },
    default: "#8b95a5",
    selected: "#f39c12",
    metalness: 0.72,
    roughness: 0.38,
  },
  grid: {
    primary: "#94a3b8",
    minor: "#cbd5e1",
    labelBackground: "#ffffff",
    labelBorder: "#cbd5e1",
    labelText: "#0f172a",
    labelShadow: "0 1px 3px rgba(15, 23, 42, 0.12)",
  },
  selection: {
    edge: "#f39c12",
  },
  placeholder: "#cbd5e1",
};

const darkTheme: ViewportTheme = {
  performance: {
    enableEnvironment: false,
    environmentMaxElements: 120,
    enableShadows: false,
    maxDpr: 1,
  },
  canvas: {
    background: "#0c0c0e",
    overlay: "rgba(12, 12, 14, 0.95)",
    border: "#27272a",
  },
  lighting: {
    ambient: 0.5,
    directional: 1,
    directionalPosition: [15, 20, 10],
    fill: 0,
    fillPosition: [-10, 12, -8],
  },
  environment: {
    preset: "warehouse",
    intensity: 0.35,
  },
  steel: {
    colors: {
      "I-beam": "#5b9bd5",
      "C-channel": "#6b8cae",
      Box: "#8b9cb3",
      Pipe: "#9aa8bc",
      Plate: "#7d8694",
      Haunch: "#4f86c6",
      RHS: "#6f9bc3",
      CHS: "#7fa6c9",
      Angle: "#8896ad",
      Tee: "#6d8eb0",
      Zed: "#6b8cae",
    },
    default: "#71717a",
    selected: "#38bdf8",
    metalness: 0.4,
    roughness: 0.45,
  },
  grid: {
    primary: "#71717a",
    minor: "#52525b",
    labelBackground: "#18181b",
    labelBorder: "#52525b",
    labelText: "#fafafa",
    labelShadow: "0 1px 4px rgba(0,0,0,0.45)",
  },
  selection: {
    edge: "#38bdf8",
  },
  placeholder: "#27272a",
};

export const VIEWPORT_THEME_MODE: ViewportThemeMode = "light";

export const viewportThemes: Record<ViewportThemeMode, ViewportTheme> = {
  light: lightTheme,
  dark: darkTheme,
};

export const viewportTheme = viewportThemes[VIEWPORT_THEME_MODE];
