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

type ImageRaster = {
  width: number;
  height: number;
  data: Uint8ClampedArray;
};

export type RegionAreaKind = "text_area" | "context_area";
export type ResizeHandle = "nw" | "ne" | "sw" | "se";

type RegionOverlayInput = {
  id?: string;
  type?: string;
  bounding_box: RegionBoundingBox;
  text_area?: RegionBoundingBox;
  context_area?: RegionBoundingBox;
  panel_area?: RegionBoundingBox;
  balloon_group_id?: string | null;
  balloon_group_area?: RegionBoundingBox;
  panel_order?: number | null;
  balloon_group_order?: number | null;
  order_in_balloon_group?: number | null;
  order_in_panel?: number | null;
  global_reading_order?: number | null;
};

type StructureOverlay = {
  id: string;
  bounding_box: RegionBoundingBox;
  order: number | null;
  region_count: number;
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

export function buildRegionDisplayLabelLookup(regions: RegionOverlayInput[]) {
  const lookup = new Map<string, string>();
  let readingIndex = 1;
  let freeTextIndex = 1;

  for (const region of regions) {
    if (!region.id) {
      continue;
    }
    if (region.type === "free_text") {
      lookup.set(region.id, `F${String(freeTextIndex).padStart(2, "0")}`);
      freeTextIndex += 1;
      continue;
    }
    lookup.set(region.id, `R${String(readingIndex).padStart(2, "0")}`);
    readingIndex += 1;
  }

  return lookup;
}

export function formatPanelOverlayLabel(overlay: StructureOverlay, fallbackIndex: number) {
  const order = overlay.order ?? fallbackIndex + 1;
  return `P${String(order).padStart(2, "0")}`;
}

export function formatBalloonGroupOverlayLabel(
  overlay: StructureOverlay,
  fallbackIndex: number,
) {
  const order = overlay.order ?? fallbackIndex + 1;
  return `G${String(order).padStart(2, "0")}`;
}

export function buildPanelOverlays(regions: RegionOverlayInput[]) {
  return buildStructureOverlays(
    regions,
    (region) =>
      region.panel_order !== undefined && region.panel_order !== null
        ? `panel-${region.panel_order}`
        : `panel-box-${buildBoundingBoxKey(region.panel_area ?? region.context_area ?? region.bounding_box)}`,
    (region) => region.panel_area ?? region.context_area ?? region.bounding_box,
    (region) => region.panel_order ?? null,
  );
}

export function buildBalloonGroupOverlays(regions: RegionOverlayInput[]) {
  return buildStructureOverlays(
    regions,
    (region) =>
      region.balloon_group_id
      ?? (
        region.balloon_group_order !== undefined && region.balloon_group_order !== null
          ? `group-${region.panel_order ?? "none"}-${region.balloon_group_order}`
          : `group-box-${buildBoundingBoxKey(region.balloon_group_area ?? region.context_area ?? region.bounding_box)}`
      ),
    (region) => region.balloon_group_area ?? region.context_area ?? region.bounding_box,
    (region) => region.balloon_group_order ?? null,
  );
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

export function refineTextAreaToDarkPixels(
  raster: ImageRaster,
  boundingBox: RegionBoundingBox,
) {
  const x1 = Math.max(Math.floor(boundingBox.x), 0);
  const y1 = Math.max(Math.floor(boundingBox.y), 0);
  const x2 = Math.min(Math.ceil(boundingBox.x + boundingBox.width), raster.width);
  const y2 = Math.min(Math.ceil(boundingBox.y + boundingBox.height), raster.height);
  if (x2 <= x1 || y2 <= y1) {
    return boundingBox;
  }

  const cropWidth = x2 - x1;
  const cropHeight = y2 - y1;
  const grayscale = new Uint8Array(cropWidth * cropHeight);
  const histogram = new Array<number>(256).fill(0);
  let index = 0;
  for (let y = y1; y < y2; y += 1) {
    for (let x = x1; x < x2; x += 1) {
      const offset = ((y * raster.width) + x) * 4;
      const gray = Math.round(
        ((raster.data[offset] ?? 0) * 0.299)
        + ((raster.data[offset + 1] ?? 0) * 0.587)
        + ((raster.data[offset + 2] ?? 0) * 0.114),
      );
      grayscale[index] = gray;
      histogram[gray] = (histogram[gray] ?? 0) + 1;
      index += 1;
    }
  }

  const threshold = clampNumber(computeOtsuThreshold(histogram), 72, 188);
  const darkCountsByColumn = new Array<number>(cropWidth).fill(0);
  const darkCountsByRow = new Array<number>(cropHeight).fill(0);
  index = 0;
  for (let y = 0; y < cropHeight; y += 1) {
    for (let x = 0; x < cropWidth; x += 1) {
      if ((grayscale[index] ?? 255) <= threshold) {
        darkCountsByColumn[x] = (darkCountsByColumn[x] ?? 0) + 1;
        darkCountsByRow[y] = (darkCountsByRow[y] ?? 0) + 1;
      }
      index += 1;
    }
  }

  suppressBoundaryArtifacts(darkCountsByColumn, cropHeight);
  suppressBoundaryArtifacts(darkCountsByRow, cropWidth);

  const isVertical = boundingBox.height >= boundingBox.width * 1.1;
  const validColumns = fillTinyAxisGaps(
    darkCountsByColumn.map((count) => count >= Math.max(2, Math.round(cropHeight * 0.06))),
  );
  const validRows = fillTinyAxisGaps(
    darkCountsByRow.map((count) =>
      count >= Math.max(2, Math.round(cropWidth * (isVertical ? 0.035 : 0.06)))
    ),
  );

  const columnRange = findActiveAxisRange(validColumns);
  const rowRange = findActiveAxisRange(validRows);
  if (columnRange === null || rowRange === null) {
    return boundingBox;
  }

  const [columnStart, columnEnd] = columnRange;
  const [rowStart, rowEnd] = rowRange;
  const selectedWidth = Math.max(columnEnd - columnStart, 1);
  const selectedHeight = Math.max(rowEnd - rowStart, 1);
  const paddingX = isVertical
    ? Math.min(6, Math.max(2, Math.round(selectedWidth * 0.08)))
    : Math.min(8, Math.max(2, Math.round(selectedWidth * 0.03)));
  const paddingY = isVertical
    ? Math.min(8, Math.max(3, Math.round(selectedHeight * 0.05)))
    : Math.min(6, Math.max(2, Math.round(selectedHeight * 0.08)));

  const nextBoundingBox = {
    x: Math.max(x1 + columnStart - paddingX, x1),
    y: Math.max(y1 + rowStart - paddingY, y1),
    width: Math.min(selectedWidth + (paddingX * 2), x2 - x1),
    height: Math.min(selectedHeight + (paddingY * 2), y2 - y1),
  };
  if (
    (boundingBox.width - nextBoundingBox.width) < 4
    && (boundingBox.height - nextBoundingBox.height) < 4
  ) {
    return boundingBox;
  }
  return nextBoundingBox;
}

function computeOtsuThreshold(histogram: number[]) {
  let total = 0;
  let sum = 0;
  for (let index = 0; index < histogram.length; index += 1) {
    total += histogram[index] ?? 0;
    sum += index * (histogram[index] ?? 0);
  }

  let sumBackground = 0;
  let weightBackground = 0;
  let maxVariance = -1;
  let threshold = 128;
  for (let index = 0; index < histogram.length; index += 1) {
    weightBackground += histogram[index] ?? 0;
    if (weightBackground === 0) {
      continue;
    }
    const weightForeground = total - weightBackground;
    if (weightForeground === 0) {
      break;
    }
    sumBackground += index * (histogram[index] ?? 0);
    const meanBackground = sumBackground / weightBackground;
    const meanForeground = (sum - sumBackground) / weightForeground;
    const variance =
      weightBackground
      * weightForeground
      * (meanBackground - meanForeground)
      * (meanBackground - meanForeground);
    if (variance > maxVariance) {
      maxVariance = variance;
      threshold = index;
    }
  }
  return threshold;
}

function suppressBoundaryArtifacts(counts: number[], oppositeAxisLength: number) {
  const boundaryLimit = oppositeAxisLength * 0.7;
  const edgeWindow = Math.min(3, counts.length);
  for (let index = 0; index < edgeWindow; index += 1) {
    if ((counts[index] ?? 0) >= boundaryLimit) {
      counts[index] = 0;
    }
    const mirroredIndex = counts.length - 1 - index;
    if ((counts[mirroredIndex] ?? 0) >= boundaryLimit) {
      counts[mirroredIndex] = 0;
    }
  }
}

function fillTinyAxisGaps(values: boolean[]) {
  if (values.length <= 2) {
    return values;
  }
  const filled = values.slice();
  for (let index = 1; index < values.length - 1; index += 1) {
    if (!values[index] && values[index - 1] && values[index + 1]) {
      filled[index] = true;
    }
  }
  return filled;
}

function findActiveAxisRange(values: boolean[]) {
  let start = -1;
  let end = -1;
  for (let index = 0; index < values.length; index += 1) {
    if (!values[index]) {
      continue;
    }
    if (start === -1) {
      start = index;
    }
    end = index + 1;
  }
  if (start === -1 || end === -1) {
    return null;
  }
  return [start, end] as const;
}

function formatBoundingBox(boundingBox: RegionBoundingBox) {
  const { x, y, width, height } = boundingBox;
  return `${Math.round(x)}, ${Math.round(y)} - ${Math.round(width)} x ${Math.round(height)}`;
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function buildStructureOverlays(
  regions: RegionOverlayInput[],
  getKey: (region: RegionOverlayInput) => string,
  getBoundingBox: (region: RegionOverlayInput) => RegionBoundingBox,
  getOrder: (region: RegionOverlayInput) => number | null,
) {
  const overlays = new Map<string, StructureOverlay>();

  for (const region of regions) {
    const key = getKey(region);
    const boundingBox = getBoundingBox(region);
    const existingOverlay = overlays.get(key);
    if (existingOverlay === undefined) {
      overlays.set(key, {
        id: key,
        bounding_box: { ...boundingBox },
        order: getOrder(region),
        region_count: 1,
      });
      continue;
    }

    overlays.set(key, {
      ...existingOverlay,
      bounding_box: mergeBoundingBoxes(existingOverlay.bounding_box, boundingBox),
      region_count: existingOverlay.region_count + 1,
    });
  }

  return Array.from(overlays.values()).sort((left, right) => {
    const leftOrder = left.order ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = right.order ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    if (left.bounding_box.y !== right.bounding_box.y) {
      return left.bounding_box.y - right.bounding_box.y;
    }
    return left.bounding_box.x - right.bounding_box.x;
  });
}

function mergeBoundingBoxes(left: RegionBoundingBox, right: RegionBoundingBox): RegionBoundingBox {
  const minX = Math.min(left.x, right.x);
  const minY = Math.min(left.y, right.y);
  const maxX = Math.max(left.x + left.width, right.x + right.width);
  const maxY = Math.max(left.y + left.height, right.y + right.height);
  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

function buildBoundingBoxKey(boundingBox: RegionBoundingBox) {
  return [
    Math.round(boundingBox.x),
    Math.round(boundingBox.y),
    Math.round(boundingBox.width),
    Math.round(boundingBox.height),
  ].join("-");
}
