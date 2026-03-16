import assert from "node:assert/strict";

import { buildPdfBinary } from "../src/features/projects/pdf.ts";

const jpegBytes = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);
const pdfBytes = buildPdfBinary({
  width: 640,
  height: 960,
  jpegBytes,
});

const pdfText = new TextDecoder().decode(pdfBytes);

assert.equal(pdfText.startsWith("%PDF-1.4"), true);
assert.equal(pdfText.includes("/Type /Catalog"), true);
assert.equal(pdfText.includes("/Subtype /Image"), true);
assert.equal(pdfText.includes("startxref"), true);

console.log("WEB_PDF_TESTS_OK");
