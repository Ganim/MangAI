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
