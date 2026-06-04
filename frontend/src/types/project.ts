export type ShapeType = "I-beam" | "C-channel" | "Box" | "Pipe";
export type SectionSource = "catalog" | "parametric";
export type ExtrusionAxis = "x" | "y" | "z";
export type ElementRotation = 0 | 90 | 180 | 270;
export type ElementAlignment = "center" | "top" | "bottom";

export interface SectionDimensionsMm {
  h: number;
  b: number;
  tw: number;
  tf: number;
}

/** Millimeter-based element from backend geometry_engine */
export interface ProjectElementMm {
  id: string;
  assembly_id?: string | null;
  shape_type: ShapeType;
  position_mm: { x: number; y: number; z: number };
  size_mm: { x: number; y: number; z: number };
  length_mm: number;
  width_mm: number;
  depth_mm: number;
  section_source?: SectionSource;
  profile_name?: string | null;
  section_mm?: SectionDimensionsMm | null;
  /** World axis along which the member is extruded (Y = vertical column) */
  axis?: ExtrusionAxis;
  /** Set when placed relative to another member */
  anchor_element_id?: string | null;
  anchor_point?: "TOP" | "BOTTOM" | "START" | "END" | "CENTER" | null;
  /** Connection nodes in backend coords (Y = vertical). */
  nodes?: Record<string, [number, number, number]>;
  /** Macro role: column, rafter, wall_girt, bracing, truss_chord, … */
  element_type?: string | null;
  /** Macro / future use: Euler rotation in degrees [rx, ry, rz] */
  rotation_euler_deg?: [number, number, number] | null;
  /** Local display rotation around vertical (Y) axis in degrees */
  rotation?: ElementRotation;
  /** Cross-section vertical alignment at the placement reference */
  alignment?: ElementAlignment;
}

export interface ProjectState {
  version: number;
  projectElements: ProjectElementMm[];
}

export const DEFAULT_ELEMENT_ROTATION: ElementRotation = 0;
export const DEFAULT_ELEMENT_ALIGNMENT: ElementAlignment = "center";

export const emptyProjectState = (): ProjectState => ({
  version: 3,
  projectElements: [],
});

export function normalizeElement(element: ProjectElementMm): ProjectElementMm {
  const rotation = (element.rotation ?? DEFAULT_ELEMENT_ROTATION) as ElementRotation;
  const alignment = element.alignment ?? DEFAULT_ELEMENT_ALIGNMENT;

  return {
    ...element,
    rotation,
    alignment,
    rotation_euler_deg: element.rotation_euler_deg ?? null,
  };
}

export function isExtrudedIBeam(element: ProjectElementMm): boolean {
  return (
    element.shape_type === "I-beam" &&
    element.section_mm != null &&
    element.section_mm.h > 0 &&
    element.section_mm.b > 0
  );
}
