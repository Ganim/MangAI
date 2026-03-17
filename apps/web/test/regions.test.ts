import assert from "node:assert/strict";

import {
  buildBalloonGroupOverlays,
  buildDefaultRegionInput,
  buildPanelOverlays,
  buildRegionDisplayLabelLookup,
  formatBalloonGroupOverlayLabel,
  formatRegionBounds,
  formatRegionIndexLabel,
  formatPanelOverlayLabel,
  formatRegionReadingOrderLabel,
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
assert.equal(
  formatRegionReadingOrderLabel(
    {
      bounding_box: {
        x: 160,
        y: 240,
        width: 320,
        height: 480,
      },
      global_reading_order: 7,
    },
    0,
  ),
  "R07",
);

const regionDisplayLabels = buildRegionDisplayLabelLookup([
  {
    id: "speech-1",
    type: "speech_balloon",
    bounding_box: { x: 0, y: 0, width: 10, height: 10 },
  },
  {
    id: "margin-1",
    type: "free_text",
    bounding_box: { x: 0, y: 0, width: 10, height: 10 },
  },
  {
    id: "speech-2",
    type: "narration_box",
    bounding_box: { x: 0, y: 0, width: 10, height: 10 },
  },
]);
assert.equal(regionDisplayLabels.get("speech-1"), "R01");
assert.equal(regionDisplayLabels.get("speech-2"), "R02");
assert.equal(regionDisplayLabels.get("margin-1"), "F01");
assert.equal(
  formatPanelOverlayLabel(
    {
      id: "panel-2",
      bounding_box: { x: 0, y: 0, width: 100, height: 100 },
      order: 2,
      region_count: 3,
    },
    0,
  ),
  "P02",
);
assert.equal(
  formatBalloonGroupOverlayLabel(
    {
      id: "group-4",
      bounding_box: { x: 0, y: 0, width: 100, height: 100 },
      order: 4,
      region_count: 2,
    },
    0,
  ),
  "G04",
);

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

const panelOverlays = buildPanelOverlays([
  {
    bounding_box: { x: 100, y: 120, width: 120, height: 180 },
    context_area: { x: 80, y: 90, width: 180, height: 260 },
    panel_area: { x: 40, y: 60, width: 420, height: 320 },
    panel_order: 2,
  },
  {
    bounding_box: { x: 280, y: 160, width: 120, height: 160 },
    context_area: { x: 250, y: 120, width: 190, height: 230 },
    panel_area: { x: 40, y: 60, width: 420, height: 320 },
    panel_order: 2,
  },
  {
    bounding_box: { x: 520, y: 80, width: 120, height: 160 },
    context_area: { x: 500, y: 60, width: 180, height: 220 },
    panel_area: { x: 500, y: 40, width: 260, height: 340 },
    panel_order: 3,
  },
]);
assert.equal(panelOverlays.length, 2);
assert.equal(panelOverlays[0]?.order, 2);
assert.deepEqual(panelOverlays[0]?.bounding_box, { x: 40, y: 60, width: 420, height: 320 });

const balloonGroupOverlays = buildBalloonGroupOverlays([
  {
    bounding_box: { x: 100, y: 120, width: 120, height: 180 },
    context_area: { x: 80, y: 90, width: 180, height: 260 },
    balloon_group_id: "group-a",
    balloon_group_area: { x: 72, y: 84, width: 192, height: 272 },
    balloon_group_order: 1,
  },
  {
    bounding_box: { x: 138, y: 142, width: 108, height: 160 },
    context_area: { x: 118, y: 112, width: 160, height: 220 },
    balloon_group_id: "group-a",
    balloon_group_area: { x: 72, y: 84, width: 192, height: 272 },
    balloon_group_order: 1,
  },
  {
    bounding_box: { x: 420, y: 180, width: 120, height: 180 },
    context_area: { x: 390, y: 150, width: 180, height: 240 },
    balloon_group_id: "group-b",
    balloon_group_area: { x: 382, y: 142, width: 196, height: 256 },
    balloon_group_order: 2,
  },
]);
assert.equal(balloonGroupOverlays.length, 2);
assert.equal(balloonGroupOverlays[0]?.order, 1);
assert.deepEqual(balloonGroupOverlays[0]?.bounding_box, {
  x: 72,
  y: 84,
  width: 192,
  height: 272,
});

console.log("WEB_REGION_TESTS_OK");
