export type ShapeType = "I-beam" | "C-channel" | "Box" | "Pipe";
export type AxisType = "x" | "y" | "z";

export interface StructuralElement {
  id: string;
  shape_type: ShapeType;
  axis: AxisType;
  position: [number, number, number];
  rotation: [number, number, number];
  size: [number, number, number];
  height: number;
  width: number;
  thickness: number;
  length: number;
  color?: string | null;
}

export interface ProjectState {
  version: number;
  elements: StructuralElement[];
}

export const emptyProjectState = (): ProjectState => ({
  version: 2,
  elements: [],
});
