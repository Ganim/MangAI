type BoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type PageDimensions = {
  width: number | null;
  height: number | null;
};

type RegionLike = {
  id: string;
  bounding_box: BoundingBox;
};

type DialogueLike = {
  id: string;
  reading_order: number;
  content: string;
};

type TranslationLike = {
  dialogue_id: string;
  target_language: string;
  content: string;
  status: string;
};

type AssignmentLike = {
  id: string;
  dialogue_id: string;
  region_id: string;
  approved: boolean;
};

type PlacementLike = {
  id: string;
  assignment_id: string;
  text_box: BoundingBox;
  style: {
    font_family: string;
    font_fallbacks?: string[];
    font_size: number;
    leading: number;
    tracking: number;
    alignment: string;
    direction: string;
    rotation: number;
    fill: string;
  };
};

export function getNextReadingOrder(dialogues: DialogueLike[]) {
  return dialogues.reduce((maxValue, dialogue) => Math.max(maxValue, dialogue.reading_order), 0) + 1;
}

export function buildDefaultPlacementInput(args: {
  assignmentId: string;
  region: RegionLike;
  targetLanguage: string;
  textDirection: "ltr" | "rtl" | "ttb";
}) {
  const regionHeight = args.region.bounding_box.height;
  const fontSize = Math.max(18, Math.round(regionHeight * 0.22));
  const leading = Math.max(fontSize + 4, Math.round(fontSize * 1.2));
  const fontFamily =
    args.targetLanguage.startsWith("pt") ? "CC Meanwhile" : "Komika Axis";

  return {
    assignment_id: args.assignmentId,
    text_box: { ...args.region.bounding_box },
    style: {
      font_family: fontFamily,
      font_fallbacks: ["Arial", "sans-serif"],
      font_size: fontSize,
      leading,
      tracking: 0,
      alignment: "center",
      direction: args.textDirection,
      rotation: 0,
      fill: "#111111",
    },
  };
}

export function getPlacementOverlayStyle(
  placement: PlacementLike,
  page: PageDimensions,
) {
  const width = page.width ?? 1000;
  const height = page.height ?? 1400;
  const box = placement.text_box;
  return {
    left: `${(box.x / width) * 100}%`,
    top: `${(box.y / height) * 100}%`,
    width: `${(box.width / width) * 100}%`,
    height: `${(box.height / height) * 100}%`,
    color: placement.style.fill,
    fontFamily: [placement.style.font_family, ...(placement.style.font_fallbacks ?? [])].join(", "),
    fontSize: `${Math.max(14, placement.style.font_size)}px`,
    lineHeight: `${Math.max(1, placement.style.leading / Math.max(1, placement.style.font_size))}`,
    letterSpacing: `${placement.style.tracking}px`,
    textAlign: placement.style.alignment as "center" | "left" | "right" | "justify",
    transform: `rotate(${placement.style.rotation}deg)`,
  } as const;
}

export function buildTextPreviewEntries(args: {
  dialogues: DialogueLike[];
  translations: TranslationLike[];
  assignments: AssignmentLike[];
  placements: PlacementLike[];
}) {
  return args.placements
    .map((placement) => {
      const assignment = args.assignments.find((candidate) => candidate.id === placement.assignment_id);
      if (!assignment || !assignment.approved) {
        return null;
      }
      const dialogue = args.dialogues.find((candidate) => candidate.id === assignment.dialogue_id);
      const translation = args.translations.find(
        (candidate) => candidate.dialogue_id === assignment.dialogue_id,
      );
      if (!dialogue || !translation || translation.content.trim().length === 0) {
        return null;
      }
      return {
        id: placement.id,
        region_id: assignment.region_id,
        reading_order: dialogue.reading_order,
        text: translation.content,
        placement,
      };
    })
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
    .sort((left, right) => left.reading_order - right.reading_order);
}
