/** Parse grid / frame references from canonical shed member ids. */

export type ParsedMemberId = {
  assemblyId: string;
  gridX: string | null;
  gridZ: string | null;
  frameZ: string | null;
  trussSegment: string | null;
  purlinIndex: number | null;
  girtWall: string | null;
};

const COL_RE = /^(.+)-col-([A-Z]+)-(\d+)$/;
const RAFTER_RE = /^(.+)-rafter(?:-(?:L|R))?-(\d+)$/;
const TRUSS_MEMBER_RE = /^(.+)-truss-(?:TC|BC|web|post)-(\d+)(?:-|$)/;
const TRUSS_CHORD_RE = /^(.+)-truss-(TC|BC)-(\d+)-(\d+)$/;
const PURLIN_RE = /^(.+)-purlin-(\d+)$/;
const GIRT_RE = /^(.+)-girt-(\w+)-L(\d+)$/;
const HAUNCH_RE = /^(.+)-haunch-(\d+)-/;
const TIE_RE = /^(.+)-tie(?:-ridge|-([A-Z]+))?$/;

export function parseMemberId(id: string): ParsedMemberId {
  const empty: ParsedMemberId = {
    assemblyId: id.split("-")[0] ?? "shed_1",
    gridX: null,
    gridZ: null,
    frameZ: null,
    trussSegment: null,
    purlinIndex: null,
    girtWall: null,
  };

  let m = id.match(COL_RE);
  if (m) {
    return {
      ...empty,
      assemblyId: m[1],
      gridX: m[2],
      gridZ: m[3],
      frameZ: m[3],
    };
  }

  m = id.match(RAFTER_RE);
  if (m) {
    return { ...empty, assemblyId: m[1], frameZ: m[2] };
  }

  m = id.match(TRUSS_CHORD_RE);
  if (m) {
    return {
      ...empty,
      assemblyId: m[1],
      frameZ: m[3],
      trussSegment: m[4],
    };
  }

  m = id.match(TRUSS_MEMBER_RE);
  if (m) {
    return { ...empty, assemblyId: m[1], frameZ: m[2] };
  }

  m = id.match(HAUNCH_RE);
  if (m) {
    return { ...empty, assemblyId: m[1], frameZ: m[2] };
  }

  m = id.match(PURLIN_RE);
  if (m) {
    return {
      ...empty,
      assemblyId: m[1],
      purlinIndex: Number(m[2]),
    };
  }

  m = id.match(GIRT_RE);
  if (m) {
    return { ...empty, assemblyId: m[1], girtWall: m[2] };
  }

  m = id.match(TIE_RE);
  if (m && m[2]) {
    return { ...empty, assemblyId: m[1], gridX: m[2] };
  }

  return empty;
}

/** Frame line index (0-based) from z label "1", "2", … */
export function frameIndexFromZLabel(zLabel: string | null): number | null {
  if (!zLabel) return null;
  const n = Number(zLabel);
  if (!Number.isFinite(n) || n < 1) return null;
  return n - 1;
}

export function frameLabelFromIndex(index: number): string {
  return String(index + 1);
}

export function isTrussMemberId(id: string): boolean {
  return /-truss-(?:TC|BC|web|post)-/.test(id);
}

export function isFramePrimaryMember(elementType: string, id: string): boolean {
  return (
    elementType === "rafter" ||
    elementType === "truss_chord" ||
    elementType === "truss_web" ||
    isTrussMemberId(id)
  );
}
