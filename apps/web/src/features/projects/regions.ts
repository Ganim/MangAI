import type { CSSProperties } from "react";

const FALLBACK_PAGE_WIDTH = 1000;
const FALLBACK_PAGE_HEIGHT = 1400;

type PageCanvasInput = {
  width: number | null;
  height: number | null;
};

type RegionBoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type RegionAreaKind = "text_area" | "context_area";
export type ResizeHandle = "nw" | "ne" | "sw" | "se";

type RegionOverlayInput = {
  bounding_box: RegionBoundingBox;
  text_area?: RegionBoundingBox;
  context_area?: RegionBoundingBox;
  panel_area?: RegionBoundingBox;
  balloon_group_area?: RegionBoundingBox;
  panel_order?: number | null;
  balloon_group_order?: number | null;
  order_in_balloon_group?: number | null;
  order_in_panel?: number | null;
  global_reading_order?: number | null;
};

const MIN_REGION_SIZE = 24;

export function getPageCanvasSize(page: PageCanvasInput) {
  return {
    width: page.width ?? FALLBACK_PAGE_WIDTH,
    height: page.height ?? FALLBACK_PAGE_HEIGHT,
    usedFallback: page.width === null || page.height === null,
  };
}

export function buildDefaultRegionInput(page: PageCanvasInput) {
  const { width, height } = getPageCanvasSize(page);
  return {
    type: "speech_balloon" as const,
    bounding_box: {
      x: Math.round(width * 0.16),
      y: Math.round(height * 0.16),
      width: Math.round(width * 0.34),
      height: Math.round(height * 0.16),
    },
  };
}

export function getRegionOverlayStyle(
  region: RegionOverlayInput,
  page: PageCanvasInput,
  area: RegionAreaKind = "context_area",
): CSSProperties {
  return getBoundingBoxOverlayStyle(getRegionAreaBoundingBox(region, area), page);
}

export function formatRegionBounds(region: RegionOverlayInput) {
  const textAreaLabel = formatBoundingBox(region.bounding_box);
  const contextArea = region.context_area;
  if (
    contextArea === undefined
    || (
      contextArea.x === region.bounding_box.x
      && contextArea.y === region.bounding_box.y
      && contextArea.width === region.bounding_box.width
      && contextArea.height === region.bounding_box.height
    )
  ) {
    return textAreaLabel;
  }
  return `Text ${textAreaLabel} | Context ${formatBoundingBox(contextArea)}`;
}

export function formatRegionIndexLabel(index: number) {
  return `R${String(index + 1).padStart(2, "0")}`;
}

export function formatRegionReadingOrderLabel(
  region: RegionOverlayInput,
  fallbackIndex: number,
) {
  const readingOrder = region.global_reading_order ?? fallbackIndex + 1;
  return `R${String(readingOrder).padStart(2, "0")}`;
}

export function moveBoundingBox(
  boundingBox: RegionBoundingBox,
  page: PageCanvasInput,
  dx: number,
  dy: number,
) {
  const { width: pageWidth, height: pageHeight } = getPageCanvasSize(page);
  const nextX = clampNumber(boundingBox.x + dx, 0, Math.max(pageWidth - boundingBox.width, 0));
  const nextY = clampNumber(boundingBox.y + dy, 0, Math.max(pageHeight - boundingBox.height, 0));
  return {
    ...boundingBox,
    x: Math.round(nextX),
    y: Math.round(nextY),
  };
}

export function resizeBoundingBox(
  boundingBox: RegionBoundingBox,
  page: PageCanvasInput,
  dw: number,
  dh: number,
) {
  const { width: pageWidth, height: pageHeight } = getPageCanvasSize(page);
  const nextWidth = clampNumber(
    boundingBox.width + dw,
    MIN_REGION_SIZE,
    Math.max(pageWidth - boundingBox.x, MIN_REGION_SIZE),
  );
  const nextHeight = clampNumber(
    boundingBox.height + dh,
    MIN_REGION_SIZE,
    Math.max(pageHeight - boundingBox.y, MIN_REGION_SIZE),
  );
  return {
    ...boundingBox,
    width: Math.round(nextWidth),
    height: Math.round(nextHeight),
  };
}

export function getBoundingBoxAdjustmentStep(page: PageCanvasInput) {
  const { width, height } = getPageCanvasSize(page);
  return Math.max(12, Math.round(Math.min(width, height) * 0.02));
}

export function getEditableRegionBoundingBox(region: RegionOverlayInput) {
  return region.context_area ?? region.bounding_box;
}

export function getRegionAreaBoundingBox(
  region: RegionOverlayInput,
  area: RegionAreaKind,
) {
  if (area === "text_area") {
    return region.text_area ?? region.bounding_box;
  }
  return region.context_area ?? region.bounding_box;
}

export function getBoundingBoxOverlayStyle(
  boundingBox: RegionBoundingBox,
  page: PageCanvasInput,
): CSSProperties {
  const { width, height } = getPageCanvasSize(page);
  return {
    left: `${(boundingBox.x / width) * 100}%`,
    top: `${(boundingBox.y / height) * 100}%`,
    width: `${(boundingBox.width / width) * 100}%`,
    height: `${(boundingBox.height / height) * 100}%`,
  };
}

export function resizeBoundingBoxFromHandle(
  boundingBox: RegionBoundingBox,
  page: PageCanvasInput,
  handle: ResizeHandle,
  dx: number,
  dy: number,
) {
  const { width: pageWidth, height: pageHeight } = getPageCanvasSize(page);
  const maxX = pageWidth;
  const maxY = pageHeight;

  let nextX = boundingBox.x;
  let nextY = boundingBox.y;
  let nextWidth = boundingBox.width;
  let nextHeight = boundingBox.height;

  if (handle.includes("w")) {
    nextX = boundingBox.x + dx;
    nextWidth = boundingBox.width - dx;
  } else {
    nextWidth = boundingBox.width + dx;
  }

  if (handle.includes("n")) {
    nextY = boundingBox.y + dy;
    nextHeight = boundingBox.height - dy;
  } else {
    nextHeight = boundingBox.height + dy;
  }

  if (nextWidth < MIN_REGION_SIZE) {
    if (handle.includes("w")) {
      nextX -= MIN_REGION_SIZE - nextWidth;
    }
    nextWidth = MIN_REGION_SIZE;
  }

  if (nextHeight < MIN_REGION_SIZE) {
    if (handle.includes("n")) {
      nextY -= MIN_REGION_SIZE - nextHeight;
    }
    nextHeight = MIN_REGION_SIZE;
  }

  if (nextX < 0) {
    if (handle.includes("w")) {
      nextWidth += nextX;
    }
    nextX = 0;
  }

  if (nextY < 0) {
    if (handle.includes("n")) {
      nextHeight += nextY;
    }
    nextY = 0;
  }

  if (nextX + nextWidth > maxX) {
    nextWidth = maxX - nextX;
  }

  if (nextY + nextHeight > maxY) {
    nextHeight = maxY - nextY;
  }

  if (nextWidth < MIN_REGION_SIZE) {
    nextWidth = MIN_REGION_SIZE;
    nextX = Math.max(0, Math.min(nextX, maxX - nextWidth));
  }

  if (nextHeight < MIN_REGION_SIZE) {
    nextHeight = MIN_REGION_SIZE;
    nextY = Math.max(0, Math.min(nextY, maxY - nextHeight));
  }

  return {
    x: Math.round(nextX),
    y: Math.round(nextY),
    width: Math.round(nextWidth),
    height: Math.round(nextHeight),
  };
}

function formatBoundingBox(boundingBox: RegionBoundingBox) {
  const { x, y, width, height } = boundingBox;
  return `${Math.round(x)}, ${Math.round(y)} - ${Math.round(width)} x ${Math.round(height)}`;
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
