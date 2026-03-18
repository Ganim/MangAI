# Typesetting Plan

## Goal

Build a TyperTools-inspired text workflow for MangAI that turns detected dialogue into editable translated placements with project-level style presets and safe manual overrides.

## Product Outcome

When this phase is complete, the user should be able to:

1. review OCR text per page
2. paste or generate translated text
3. import scripts using page markers like `[1]`, `[2]`, `[3]`
4. bind each line to the correct balloon or region
5. apply a style preset
6. generate placements automatically
7. fine-tune typography manually without losing work

## Design Principles

- dialogue is the primary unit of text work
- region is the primary unit of visual placement
- OCR text and translated text must be visible side by side
- script import must support batch workflows without breaking page-level review
- auto-typesetting must be reversible and non-destructive
- manual layout edits always win over later automation
- presets belong to the project and can be copied between projects

## Current Foundation

The current codebase already contains the core entities needed to support this phase:

- `Dialogue`
- `Translation`
- `Assignment`
- `TextPlacement`
- `TextStyle`

References:

- [entities.ts](D:/Code/Projetos/MangAI/packages/shared/src/entities.ts)
- [contracts.ts](D:/Code/Projetos/MangAI/packages/shared/src/contracts.ts)
- [page-editor-shell.tsx](D:/Code/Projetos/MangAI/apps/web/src/components/page-editor-shell.tsx)

## Missing Capabilities

The current foundation is still missing these product-level pieces:

- dual text panels for source and translated text
- script import parser with page markers
- project-level preset library
- preset copy workflow between projects
- stronger auto-typesetting controls
- placement locking and reflow safety
- structured typesetting metrics and preview state

## Domain Additions

### StylePreset

Add a new entity for reusable project-level typography presets.

Suggested fields:

- `id`
- `project_id`
- `name`
- `category`
- `is_default`
- `style`
- `created_at`
- `updated_at`

### Extended TextStyle

Expand `TextStyle` to support real production presets.

Suggested additions:

- `min_font_size`
- `max_font_size`
- `padding_x`
- `padding_y`
- `line_break_mode`
- `stroke_fill`
- `stroke_width`
- `uppercase`
- `auto_fit`
- `vertical_bias`
- `allow_overflow`

### Dialogue Import Metadata

Add import-related metadata to `Dialogue` so script workflows are traceable.

Suggested additions:

- `script_row_index`
- `page_marker`
- `import_batch_id`
- `preferred_style_preset_id`

### Placement Safety Metadata

Add fields to `TextPlacement` so reflow can be controlled safely.

Suggested additions:

- `locked_by_user`
- `manual_line_breaks`
- `layout_status`
- `overflow_detected`
- `fit_score`

## UI Architecture

### Left Text Workspace

Add a dedicated text workspace to the editor with two synchronized panels:

- `Extracted text`
- `Translated text`

Each line should show:

- reading order label
- linked region or unmatched state
- dialogue status
- translation status
- active style preset

### Script Import Surface

Add a large text input flow for pasting translation scripts.

Supported format:

```text
[1]
Line 1
Line 2

[2]
Line 1
Line 2
```

Rules:

- a page marker starts a new page block
- each non-empty line becomes one dialogue candidate
- blank lines are ignored
- unmatched surplus lines are preserved for review

### Style Preset Library

Add a style library panel with:

- preset list
- preset editor
- duplicate preset
- rename preset
- set default preset
- copy presets from another project

### Typesetting Controls

The selected dialogue or placement should expose:

- preset selector
- font family
- font size
- min and max size
- leading
- tracking
- alignment
- padding
- auto-fit toggle
- lock placement toggle

## Workflow Definition

### Flow 1: OCR Review

1. OCR produces ordered dialogues for a page.
2. User reviews or edits extracted text.
3. Each dialogue remains linked to `source_region_id`.

### Flow 2: Translation Review

1. User clicks translate or pastes translation manually.
2. Translation is stored per `dialogue_id`.
3. User edits any line before applying layout.

### Flow 3: Script Import

1. User opens import dialog.
2. User pastes text with optional page markers.
3. Parser returns per-page line blocks.
4. User confirms mapping.
5. Dialogues or translations are updated.

### Flow 4: Automatic Typesetting

1. System reads `translation + assignment + context_area + preset`.
2. Placement box is generated inside the assigned `context_area`.
3. Text is fit using preset rules.
4. Placement is saved as editable structured state.

### Flow 5: Manual Override

1. User changes box size, line breaks, or style.
2. Placement becomes `locked_by_user`.
3. Later reflow skips locked placements unless explicitly reset.

## Parser Specification

### Input Modes

- source script import
- translated script import

### Parsing Rules

- page markers follow the pattern `^[[]\\d+[]]$`
- text before the first page marker belongs to the active page only if the user is importing from inside a page editor
- duplicated page markers merge into the same page block in import preview but must warn the user
- empty lines are ignored
- whitespace-only lines are ignored
- line order inside a page block is preserved

### Import Result

The parser should return:

- pages found
- lines per page
- warnings
- unmatched pages
- total line count

## Typesetting Engine Specification

### Input

- translated text
- assignment
- region `context_area`
- style preset
- project target language
- target text direction

### Output

- `TextPlacement`
- layout metrics
- fit diagnostics

### Initial Layout Rules

- fit text inside `context_area`
- use preset paddings
- shrink font size until it fits or reaches `min_font_size`
- compute line breaks automatically
- center visually by default for speech balloons
- preserve rectangular alignment for narration boxes

### Layout Classes

Initial categories:

- `normal`
- `thoughts`
- `shout`
- `narration_box`
- `sfx`
- `handwritten`

## API Contracts To Add

### Script Import

- `POST /projects/:projectId/script-imports/parse`
- `POST /projects/:projectId/script-imports/apply`

### Style Presets

- `GET /projects/:projectId/style-presets`
- `POST /projects/:projectId/style-presets`
- `PATCH /projects/:projectId/style-presets/:presetId`
- `DELETE /projects/:projectId/style-presets/:presetId`
- `POST /projects/:projectId/style-presets/copy-from-project`

### Typesetting

- `POST /projects/:projectId/pages/:pageId/typesetting/apply`
- `POST /projects/:projectId/pages/:pageId/typesetting/reflow`

## Execution Plan

### Phase 1: Typesetting Contracts

Deliver:

- `StylePreset` entity
- extended `TextStyle`
- import parser request and response contracts
- placement lock and metrics additions

Done when:

- shared contracts fully describe the typesetting domain
- tests exist for all new parsers and schema additions

### Phase 2: Script Panel And Import Parser

Deliver:

- dual text workspace in the editor
- parser for `[1]`, `[2]`, `[3]`
- import preview
- apply imported lines to dialogues or translations

Done when:

- user can paste a multi-page script and review the result before applying it

### Phase 3: Style Preset Library

Deliver:

- project preset CRUD
- default preset selection
- category tagging
- preset copy between projects

Done when:

- a project can store and reuse named typesetting styles

### Phase 4: Automatic Typesetting Engine

Deliver:

- assignment-aware placement generation
- preset-driven auto-fit
- layout metrics persistence

Done when:

- translated text can be placed automatically inside assigned regions

### Phase 5: Manual Typesetting Controls

Deliver:

- placement lock
- line break overrides
- manual preset changes
- reflow with safe override behavior

Done when:

- users can refine typography without losing manual decisions

### Phase 6: Export Alignment

Deliver:

- editor preview aligned with final export
- preset-aware export rendering
- stable output for JPG, PSD, and PDF

Done when:

- exported text matches the editor result closely enough for trustable review

## Ticket Breakdown

### P1-T1 Shared entity design

- add `StylePreset`
- extend `TextStyle`
- extend `Dialogue`
- extend `TextPlacement`

### P1-T2 Shared parser coverage

- add contract parsers
- add validation tests

### P1-T3 API contract additions

- style preset endpoints
- script import endpoints
- typesetting endpoints

### P2-T1 Script parser core

- parse markers
- preserve line order
- collect warnings

### P2-T2 Script import preview UI

- raw input editor
- preview by page
- apply and cancel actions

### P2-T3 Editor dual text panels

- extracted text panel
- translated text panel
- selection sync with region

### P3-T1 Style preset storage

- API persistence
- project default preset

### P3-T2 Preset editor UI

- form controls
- duplicate
- rename
- delete

### P3-T3 Preset copy flow

- source project picker
- copy selected presets

### P4-T1 Typesetting heuristics v1

- width and height fit
- break lines
- align by region type

### P4-T2 Placement generation route

- create placements for selected page

### P4-T3 Editor preview integration

- render placements live on canvas

### P5-T1 Manual placement lock

- lock and unlock
- skip locked placements during reflow

### P5-T2 Manual text flow controls

- line breaks
- preset override
- font size override

### P6-T1 Export consistency check

- verify editor preview and export use same data and style values

## Test Strategy

### Shared

- contract parsing
- enum validation
- style preset validation
- script import payload validation

### API

- preset CRUD
- script parse/apply
- typesetting apply/reflow

### Web

- script parser UI behavior
- selection sync between line and region
- preset editor behavior
- placement lock behavior

### Worker

- typesetting generation heuristics
- reflow safety

### End-to-End

- upload page
- OCR extraction
- paste translation script
- apply preset
- generate placements
- adjust placement
- export preview

## Acceptance Criteria For This Whole Phase

- user can manage extracted and translated text side by side
- user can paste a multi-page script with `[1]` style markers
- presets can be saved per project
- presets can be copied to another project
- auto-typesetting works for standard balloons
- manual edits are preserved after automation
- editor preview and export remain consistent

## Recommended Start

Start with:

1. `Phase 1: Typesetting Contracts`
2. `Phase 2: Script Panel And Import Parser`

This keeps the implementation incremental, testable, and aligned with the current MangAI architecture.
