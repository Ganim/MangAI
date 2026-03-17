import assert from "node:assert/strict";

import {
  buildDefaultRegionInput,
  formatRegionBounds,
  formatRegionIndexLabel,
  getBoundingBoxAdjustmentStep,
  getPageCanvasSize,
  getRegionOverlayStyle,
  moveBoundingBox,
  resizeBoundingBox,
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

assert.equal(getBoundingBoxAdjustmentStep({ width: 1600, height: 2400 }), 32);

console.log("WEB_REGION_TESTS_OK");
