type PolygonPoint = {
  x: number;
  y: number;
};

type PolygonShape = {
  type: string;
  points: PolygonPoint[];
};

type RegionLike = {
  id: string;
  type?: string;
  state?: string;
  shape: PolygonShape;
};

type MaskRevisionLike = {
  id: string;
  region_id: string;
  version: number;
  is_active: boolean;
  approved: boolean;
  shape: PolygonShape;
};

export function buildMaskRevisionInputFromRegion(region: RegionLike) {
  return {
    region_id: region.id,
    shape: {
      type: "polygon" as const,
      points: region.shape.points.map((point) => ({ x: point.x, y: point.y })),
    },
  };
}

export function getActiveMaskRevisionForRegion(
  maskRevisions: MaskRevisionLike[],
  regionId: string,
) {
  return maskRevisions
    .filter((maskRevision) => maskRevision.region_id === regionId && maskRevision.is_active)
    .sort((left, right) => right.version - left.version)[0] ?? null;
}

export function countApprovedActiveMaskRevisions(maskRevisions: MaskRevisionLike[]) {
  return maskRevisions.filter((maskRevision) => maskRevision.is_active && maskRevision.approved).length;
}

export function hasApprovedActiveMaskRevisions(maskRevisions: MaskRevisionLike[]) {
  return countApprovedActiveMaskRevisions(maskRevisions) > 0;
}

export function getCleanupMaskCandidateRegions(regions: RegionLike[]) {
  return regions.filter((region) => region.state !== "rejected");
}
