import assert from "node:assert/strict";

import {
  buildJpegExportFileName,
  buildPdfExportFileName,
  buildPsdExportFileName,
  getPreferredExportAssetPath,
  wrapTextForPlacement,
} from "../src/features/projects/export.ts";

assert.equal(buildJpegExportFileName("001.png"), "001-export.jpg");
assert.equal(buildJpegExportFileName("page"), "page-export.jpg");
assert.equal(buildPdfExportFileName("001.png"), "001-export.pdf");
assert.equal(buildPsdExportFileName("001.png"), "001-export.psd");

assert.equal(
  getPreferredExportAssetPath({
    file_name: "001.png",
    original_asset_path: "/api/v1/projects/p/pages/a/original",
    active_cleaned_asset_path: "/api/v1/projects/p/assets/c",
    width: 1000,
    height: 1400,
  }),
  "/api/v1/projects/p/assets/c",
);

assert.equal(
  getPreferredExportAssetPath({
    file_name: "001.png",
    original_asset_path: "/api/v1/projects/p/pages/a/original",
    active_cleaned_asset_path: null,
    width: 1000,
    height: 1400,
  }),
  "/api/v1/projects/p/pages/a/original",
);

assert.deepEqual(
  wrapTextForPlacement("This is a longer exported text line for testing", 180, 24),
  ["This is a", "longer", "exported", "text line", "for testing"],
);

assert.deepEqual(wrapTextForPlacement("   ", 180, 24), []);

console.log("WEB_EXPORT_TESTS_OK");
