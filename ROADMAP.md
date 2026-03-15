# Roadmap

## Phase 0 - Foundation

Goal: turn the concept into a buildable product plan.

- define product scope and user roles
- define project data model
- define AI provider abstraction
- define export strategy for PSD, JPG, and PDF
- define the MVP editor flow

Exit criteria:

- PRD approved
- architecture approved
- MVP backlog prioritized

## Phase 1 - Project Skeleton

Goal: create the application skeleton and baseline infrastructure.

- create the monorepo layout
- set up monorepo structure
- create web app shell
- create API service shell
- create worker service shell
- set up Postgres, Redis, and object storage
- set up auth and project creation

Exit criteria:

- user can create a project
- user can upload pages
- jobs can be enqueued and tracked
- local development structure is ready for implementation

## Phase 2 - Detection and Review

Goal: make pages machine-readable and editable.

- text region detection
- balloon and narration region tagging
- editable mask interface
- page viewer with overlays
- before/after visual diff

Exit criteria:

- user can inspect and correct detected regions
- region edits persist in project state

## Phase 3 - Cleanup Engine

Goal: produce usable cleaned art.

- masked cleanup pipeline
- background reconstruction pipeline
- multiple cleanup variants for difficult regions
- confidence scoring per region
- approval or retry workflow

Exit criteria:

- user can generate cleaned art
- user can accept or redo difficult regions

## Phase 4 - OCR and Text Intake

Goal: extract or import text for composition.

- OCR extraction per region
- script import workflow
- text region ordering
- manual correction screen

Exit criteria:

- project stores approved source text per page

## Phase 5 - Translation and Matching

Goal: connect text content to visual targets.

- AI-assisted translation
- glossary-ready translation pipeline
- speech-to-balloon matching
- manual reassignment UI

Exit criteria:

- every approved line can be linked to a target region

## Phase 6 - Typesetting

Goal: restore readable and attractive dialogue.

- balloon-aware auto typesetting
- style presets
- line break and font size heuristics
- manual move/resize/edit interactions
- preview against cleaned art

Exit criteria:

- user can finalize page text visually
- text layout can be edited without leaving the app

## Phase 7 - Export

Goal: produce professional deliverables.

- JPG export
- PDF export
- PSD export
- batch export
- export presets

Exit criteria:

- user can export a finished page set in at least JPG and PSD

## Phase 8 - Production Features

Goal: make the product viable for teams and larger projects.

- chapter view
- batch translation tools
- reusable style presets
- glossary and character notes
- review states and approvals
- audit log

## Recommended MVP Cut

The fastest credible MVP is:

- project creation
- upload pages
- text detection
- editable masks
- AI cleanup
- OCR or manual text input
- balloon matching review
- auto typesetting
- JPG export
- PSD export

## Post-MVP Expansion

- translation memory
- collaboration
- version history
- SFX workflows
- consistency checks
- chapter-wide exports
