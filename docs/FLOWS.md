# User Flows

## Flow 1: Create Project and Upload Pages

### Goal

Allow the user to create a project and upload one or more pages without friction.

### Steps

1. User clicks `New Project`.
2. User defines project name and optional metadata.
3. User uploads one page, multiple pages, or a compressed batch.
4. System validates file type, size, and image readability.
5. System stores original assets and creates `Page` records.
6. System shows upload progress and per-file status.
7. User lands in the project page list.

### Acceptance Criteria

- The user can upload at least JPG, PNG, TIFF, and WEBP.
- Failed uploads do not block successful uploads.
- The system preserves original file names.
- A project is usable immediately after upload.

### Failure Cases

- unsupported file type
- corrupted file
- partial batch failure
- storage timeout

## Flow 2: Detect Text Regions

### Goal

Turn raw pages into machine-readable editing targets.

### Steps

1. User triggers `Analyze Pages`.
2. System creates detection jobs.
3. Worker detects candidate text regions and classifies region type.
4. System stores regions, overlays, and confidence values.
5. User sees detection overlays on each page.

### Acceptance Criteria

- The user can see all detected regions on top of the page.
- Each region stores its type and confidence.
- Detection can be retried page-by-page.

### Failure Cases

- no regions found
- model timeout
- low-confidence page

## Flow 3: Review and Correct Masks

### Goal

Ensure cleanup targets are safe before image editing happens.

### Steps

1. User opens a page in the editor.
2. System displays proposed regions and masks.
3. User adjusts mask shape, deletes false positives, or adds missing regions.
4. System saves revisions as structured project state.

### Acceptance Criteria

- Mask edits persist.
- User can add, remove, and resize regions.
- Original detection remains auditable.

### Failure Cases

- invalid polygon
- overlapping region ambiguity
- stale editor state

## Flow 4: Clean Art

### Goal

Remove text and reconstruct the art while preserving style.

### Steps

1. User triggers cleanup on a page or page batch.
2. System creates cleanup jobs using reviewed masks.
3. Worker performs region-aware cleanup.
4. System stores one or more cleanup results.
5. User compares original and cleaned art.
6. User accepts, retries, or requests a variant.

### Acceptance Criteria

- Cleanup results are versioned.
- User can inspect before/after state.
- Difficult regions can produce alternative attempts.

### Failure Cases

- invented or distorted background
- poor line art reconstruction
- mismatch between cleaned art and region mask

## Flow 5: OCR or Manual Text Intake

### Goal

Capture source dialogue in a reviewable format.

### Steps

1. User runs OCR or imports text manually.
2. System links OCR output to regions.
3. User reviews extracted source text.
4. User edits text where OCR failed.

### Acceptance Criteria

- OCR output is editable.
- Each line is linked to a page and region when possible.
- Manual text input can bypass OCR completely.

### Failure Cases

- OCR misses vertical or stylized text
- wrong reading order
- duplicate lines

## Flow 6: Translation Review

### Goal

Generate or import translated text while keeping human control.

### Steps

1. User triggers translation or pastes translated lines.
2. System stores the translation candidate.
3. User reviews wording, tone, and terminology.
4. User approves or edits each translated line.

### Acceptance Criteria

- Translation never overwrites source text.
- Approved and draft states are visible.
- User can work fully manually if desired.

### Failure Cases

- wrong tone
- lost context
- inconsistent terminology

## Flow 7: Match Speech to Balloons

### Goal

Associate each approved line with the correct visual region.

### Steps

1. System proposes region-to-dialogue matches.
2. User reviews a page-level assignment list.
3. User reassigns lines when necessary.
4. System stores final mapping.

### Acceptance Criteria

- Every active line can be assigned to a region.
- One page can contain unassigned lines and unassigned regions during editing.
- Final export requires all required lines to be resolved.

### Failure Cases

- wrong reading order
- multiple similar balloons
- narration vs speech confusion

## Flow 8: Typesetting

### Goal

Place translated text in a readable, attractive, editable way.

### Steps

1. System generates an initial layout per region.
2. User inspects line breaks, font size, spacing, and centering.
3. User edits text formatting or placement.
4. System saves text placement and style settings.

### Acceptance Criteria

- Layout is editable per region.
- Project or page style presets can be applied.
- User can override automation without fighting the tool.

### Failure Cases

- overflow
- poor centering
- bad line breaks
- unreadable font size

## Flow 9: Export

### Goal

Produce deliverables for review and production.

### Steps

1. User selects export type and scope.
2. System validates project completeness.
3. Worker renders outputs.
4. User downloads generated files.

### Acceptance Criteria

- JPG and PSD export work in MVP.
- Export errors are explicit and recoverable.
- Output matches the approved editor state.

### Failure Cases

- missing fonts
- incomplete page state
- PSD export mismatch
