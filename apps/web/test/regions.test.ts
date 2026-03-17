import assert from "node:assert/strict";

import {
  buildDefaultRegionInput,
  formatRegionBounds,
  formatRegionIndexLabel,
  getBoundingBoxOverlayStyle,
  getBoundingBoxAdjustmentStep,
  getPageCanvasSize,
  getRegionAreaBoundingBox,
  getRegionOverlayStyle,
  moveBoundingBox,
  resizeBoundingBox,
  resizeBoundingBoxFromHandle,
} from "../src/features/projects/regions.ts";

const canvasSize = getPageCanvasSize({ width: 1600, height: 2400 });
assert.equal(canvasSize.width, 1600);
assert.equal(canvasSize.height, 2400);
assert.equal(canvasSize.usedFallback, false);

const fallbackCanvas = getPageCanvasSize({ width: null, height: null });
assert.equal(fallbackCanvas.width, 1000);
assert.equal(fallbackCanvas.height, 1400);
assert.equal(fallbackCanvas.usedFallback, true);

const defaultRegion = buildDefaultRegionInput({ width: 1600, height: 2400 });
assert.equal(defaultRegion.type, "speech_balloon");
assert.equal(defaultRegion.bounding_box.x, 256);
assert.equal(defaultRegion.bounding_box.height, 384);

const overlayStyle = getRegionOverlayStyle(
  {
    bounding_box: {
      x: 160,
      y: 240,
      width: 320,
      height: 480,
    },
    context_area: {
      x: 120,
      y: 180,
      width: 400,
      height: 540,
    },
  },
  { width: 1600, height: 2400 },
);

assert.equal(overlayStyle.left, "7.5%");
assert.equal(overlayStyle.top, "7.5%");
assert.equal(overlayStyle.width, "25%");
assert.equal(overlayStyle.height, "22.5%");
const textOverlayStyle = getRegionOverlayStyle(
  {
    bounding_box: {
      x: 160,
      y: 240,
      width: 320,
      height: 480,
    },
    text_area: {
      x: 170,
      y: 250,
      width: 200,
      height: 300,
    },
    context_area: {
      x: 120,
      y: 180,
      width: 400,
      height: 540,
    },
  },
  { width: 1600, height: 2400 },
  "text_area",
);
assert.equal(textOverlayStyle.left, "10.625%");
assert.equal(textOverlayStyle.width, "12.5%");

assert.deepEqual(
  getRegionAreaBoundingBox(
    {
      bounding_box: {
        x: 160,
        y: 240,
        width: 320,
        height: 480,
      },
      text_area: {
        x: 170,
        y: 250,
        width: 200,
        height: 300,
      },
      context_area: {
        x: 120,
        y: 180,
        width: 400,
        height: 540,
      },
    },
    "text_area",
  ),
  {
    x: 170,
    y: 250,
    width: 200,
    height: 300,
  },
);

const directOverlayStyle = getBoundingBoxOverlayStyle(
  {
    x: 200,
    y: 300,
    width: 400,
    height: 600,
  },
  { width: 1600, height: 2400 },
);
assert.equal(directOverlayStyle.left, "12.5%");
assert.equal(directOverlayStyle.height, "25%");
assert.equal(formatRegionBounds({ bounding_box: defaultRegion.bounding_box }), "256, 384 - 544 x 384");
assert.equal(
  formatRegionBounds({
    bounding_box: { x: 160, y: 240, width: 320, height: 480 },
    context_area: { x: 120, y: 180, width: 400, height: 540 },
  }),
  "Text 160, 240 - 320 x 480 | Context 120, 180 - 400 x 540",
);
assert.equal(formatRegionIndexLabel(0), "R01");
assert.equal(formatRegionIndexLabel(11), "R12");

const movedBox = moveBoundingBox(
  {
    x: 20,
    y: 30,
    width: 100,
    height: 80,
  },
  { width: 300, height: 400 },
  40,
  -50,
);

assert.deepEqual(movedBox, {
  x: 60,
  y: 0,
  width: 100,
  height: 80,
});

const resizedBox = resizeBoundingBox(
  {
    x: 220,
    y: 320,
    width: 60,
    height: 50,
  },
  { width: 300, height: 400 },
  80,
  100,
);

assert.deepEqual(resizedBox, {
  x: 220,
  y: 320,
  width: 80,
  height: 80,
});

const resizedFromHandle = resizeBoundingBoxFromHandle(
  {
    x: 120,
    y: 100,
    width: 160,
    height: 180,
  },
  { width: 500, height: 600 },
  "nw",
  -20,
  -30,
);

assert.deepEqual(resizedFromHandle, {
  x: 100,
  y: 70,
  width: 180,
  height: 210,
});

assert.equal(getBoundingBoxAdjustmentStep({ width: 1600, height: 2400 }), 32);

console.log("WEB_REGION_TESTS_OK");
