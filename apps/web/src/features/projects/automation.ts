type RegionLike = {
  id?: string;
  type: string;
  state: string;
};

type DialogueLike = {
  id: string;
};

type AssignmentLike = {
  dialogue_id: string;
  region_id?: string;
  approved: boolean;
};

const OCR_REGION_TYPES = new Set(["speech_balloon", "narration_box", "free_text", "unknown"]);

export function countOcrCandidateRegions(regions: RegionLike[]) {
  return regions.filter(
    (region) => region.state !== "rejected" && OCR_REGION_TYPES.has(region.type),
  ).length;
}

export function countUnassignedDialogues(
  dialogues: DialogueLike[],
  assignments: AssignmentLike[],
) {
  const approvedDialogueIds = new Set(
    assignments
      .filter((assignment) => assignment.approved)
      .map((assignment) => assignment.dialogue_id),
  );
  return dialogues.filter((dialogue) => !approvedDialogueIds.has(dialogue.id)).length;
}

export function countAvailableMatchingRegions(
  regions: RegionLike[],
  assignments: AssignmentLike[],
) {
  const occupiedRegionIds = new Set(
    assignments
      .filter((assignment) => assignment.approved && typeof assignment.region_id === "string")
      .map((assignment) => assignment.region_id as string),
  );
  return regions.filter(
    (region) => region.state !== "rejected" && OCR_REGION_TYPES.has(region.type),
  ).filter((region) => !occupiedRegionIds.has(region.id ?? "")).length;
}
