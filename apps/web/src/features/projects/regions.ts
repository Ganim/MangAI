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

type RegionOverlayInput = {
  bounding_box: RegionBoundingBox;
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
): CSSProperties {
  const { width, height } = getPageCanvasSize(page);
  return {
    left: `${(region.bounding_box.x / width) * 100}%`,
    top: `${(region.bounding_box.y / height) * 100}%`,
    width: `${(region.bounding_box.width / width) * 100}%`,
    height: `${(region.bounding_box.height / height) * 100}%`,
  };
}

export function formatRegionBounds(region: RegionOverlayInput) {
  const { x, y, width, height } = region.bounding_box;
  return `${Math.round(x)}, ${Math.round(y)} - ${Math.round(width)} x ${Math.round(height)}`;
}

export function formatRegionIndexLabel(index: number) {
  return `R${String(index + 1).padStart(2, "0")}`;
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

function clampNumber(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
