export type IFCType =
  | "IfcColumn"
  | "IfcBeam"
  | "IfcMember"
  | "IfcPlate";

export type AssemblyType =
  | "BUILDING"
  | "PORTAL"
  | "TRUSS"
  | "ROOF"
  | "WALL_SIDE"
  | "WALL_GABLE"
  | "LONGITUDINAL"
  | "BRACING"
  | "MEMBER";

export interface IFCNode {
  id: string;
  x: number;
  y: number;
  z: number;
}

export interface IFCEntity {
  id: string;
  start_node_id: string;
  end_node_id: string;
  ifc_type: IFCType;
  structural_role: string;
  profile_family: string;
  local_rotation: number;
  primary_assembly_id: string;
  assembly_ids: string[];
}

export interface StructuralAssembly {
  id: string;
  label: string;
  assembly_type: AssemblyType;
  parent_id: string | null;
  entity_ids: string[];
}

export interface StructuralTopology {
  building_id: string;
  nodes: Record<string, IFCNode>;
  entities: IFCEntity[];
  assemblies: Record<string, StructuralAssembly>;
  entity_assemblies: Record<string, string[]>;
}
