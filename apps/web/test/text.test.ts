import assert from "node:assert/strict";

import {
  buildDefaultPlacementInput,
  buildTextPreviewEntries,
  getNextReadingOrder,
  getPlacementOverlayStyle,
} from "../src/features/projects/text.ts";

const region = {
  id: "11111111-1111-4111-8111-111111111111",
  bounding_box: {
    x: 120,
    y: 180,
    width: 320,
    height: 180,
  },
};

assert.equal(getNextReadingOrder([]), 1);
assert.equal(getNextReadingOrder([{ id: "a", reading_order: 2, content: "x" }]), 3);

const placementInput = buildDefaultPlacementInput({
  assignmentId: "22222222-2222-4222-8222-222222222222",
  region,
  targetLanguage: "pt-BR",
  textDirection: "ltr",
});

assert.equal(placementInput.assignment_id, "22222222-2222-4222-8222-222222222222");
assert.equal(placementInput.style.direction, "ltr");
assert.equal(placementInput.style.font_family, "CC Meanwhile");

const overlayStyle = getPlacementOverlayStyle(
  {
    id: "33333333-3333-4333-8333-333333333333",
    assignment_id: placementInput.assignment_id,
    text_box: placementInput.text_box,
    style: placementInput.style,
  },
  { width: 960, height: 1440 },
);

assert.equal(overlayStyle.left, "12.5%");
assert.equal(overlayStyle.width, "33.33333333333333%");

const previewEntries = buildTextPreviewEntries({
  dialogues: [
    { id: "d1", reading_order: 2, content: "orig 2" },
    { id: "d2", reading_order: 1, content: "orig 1" },
  ],
  translations: [
    { dialogue_id: "d1", target_language: "pt-BR", content: "Linha 2", status: "approved" },
    { dialogue_id: "d2", target_language: "pt-BR", content: "Linha 1", status: "approved" },
  ],
  assignments: [
    { id: "a1", dialogue_id: "d1", region_id: "r2", approved: true },
    { id: "a2", dialogue_id: "d2", region_id: "r1", approved: true },
  ],
  placements: [
    {
      id: "p1",
      assignment_id: "a1",
      text_box: placementInput.text_box,
      style: placementInput.style,
    },
    {
      id: "p2",
      assignment_id: "a2",
      text_box: placementInput.text_box,
      style: placementInput.style,
    },
  ],
});

assert.equal(previewEntries.length, 2);
assert.equal(previewEntries[0]?.text, "Linha 1");
assert.equal(previewEntries[1]?.text, "Linha 2");

console.log("WEB_TEXT_TESTS_OK");
