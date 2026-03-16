import assert from "node:assert/strict";

import { buildPsdBinary } from "../src/features/projects/psd.ts";

const width = 2;
const height = 2;
const rgba = new Uint8ClampedArray([
  255, 0, 0, 255,
  0, 255, 0, 255,
  0, 0, 255, 255,
  255, 255, 255, 255,
]);

const psdBytes = buildPsdBinary({
  width,
  height,
  compositeRgba: rgba,
  layers: [
    {
      name: "Layer 1",
      width,
      height,
      rgba,
    },
  ],
});

const header = new TextDecoder().decode(psdBytes.slice(0, 4));
const bytesText = new TextDecoder().decode(psdBytes);

assert.equal(header, "8BPS");
assert.equal(bytesText.includes("Layer 1"), true);
assert.equal(psdBytes.length > 100, true);

console.log("WEB_PSD_TESTS_OK");
