# MangAI

MangAI is an AI-first, human-assisted web tool for cleaning comic and manga pages, translating dialogue, placing text back into balloons, and exporting production-ready files for review and finishing in Photoshop.

## Vision

MangAI exists to automate the repetitive 70-90% of comic localization work while preserving professional control over the final result.

The product is designed for translators, redrawers, cleaners, typesetters, and studios that need:

- automatic text cleanup inside balloons
- cleanup of text placed over scenery
- background reconstruction with style preservation
- OCR and translation assistance
- automatic speech-to-balloon matching
- beautiful, editable typesetting
- export to PSD, JPG, and PDF

## Product Principles

- AI-first, not AI-only
- Human review at every critical step
- PSD export is a first-class workflow
- Every automated step must remain editable
- The project file, not the PSD, is the system of record
- Internationalization must be built in from the start

## Core Workflow

1. Upload a page or chapter.
2. Detect text, balloons, narration boxes, and text over scenery.
3. Generate editable masks.
4. Clean the art with localized image editing and inpainting.
5. Extract text with OCR or import a script manually.
6. Translate with AI assistance and human review.
7. Match each line to its target balloon.
8. Apply automatic typesetting with editable layout controls.
9. Export PSD, JPG, and PDF outputs.

## MVP Scope

The first version should focus on one-page and small-batch workflows.

Included in MVP:

- project creation and page upload
- automatic text region detection
- editable mask review
- AI cleanup with before/after comparison
- OCR extraction
- manual text import
- speech-to-balloon matching review
- automatic balloon typesetting
- manual typography adjustments
- export to JPG and PSD

Out of scope for MVP:

- real-time collaboration
- advanced glossary and translation memory
- sophisticated SFX placement
- chapter-wide consistency automation
- role-based permissions
- billing and subscriptions

## System Overview

MangAI should be built around a canonical project document that stores:

- source page assets
- detected regions
- cleanup masks
- cleaned art outputs
- OCR text
- translated text
- bubble assignments
- typography settings
- export settings

Suggested high-level architecture:

- `web-app`: Next.js app for project management and the visual editor
- `api`: FastAPI service for orchestration and project APIs
- `workers`: GPU/CPU workers for detection, OCR, cleanup, translation, and export jobs
- `db`: Postgres for projects, pages, jobs, users, and editor state
- `storage`: object storage for page assets and exports
- `queue`: Redis + Celery for background processing

## Export Philosophy

Exports should be generated from project state instead of becoming the primary source of truth.

Primary outputs:

- `PSD`: layered output for Photoshop finishing
- `JPG`: quick preview and review output
- `PDF`: chapter or batch review output

## Initial Success Metrics

- reduce manual cleanup time per page
- reduce manual typesetting time per page
- keep correction time low after AI output
- produce PSD files that remain useful in Photoshop workflows
- maintain high trust in cleanup quality

## Suggested Repository Structure

```text
.
|-- README.md
|-- ROADMAP.md
|-- TODO.md
|-- docs/
|   |-- PRD.md
|   |-- ARCHITECTURE.md
|   |-- I18N.md
|   |-- PLANNING_REVIEW.md
|   |-- FLOWS.md
|   |-- MVP.md
|   |-- DOMAIN_MODEL.md
|   |-- SCHEMA_V1.md
|   |-- PIPELINES.md
|   |-- EDITOR_UX.md
|   |-- QUALITY.md
|   |-- RISKS.md
|   |-- DECISIONS.md
|   |-- API_CONTRACTS.md
|   |-- BACKLOG.md
|   `-- MONOREPO.md
|-- apps/
|   `-- web/
|-- services/
|   |-- api/
|   `-- workers/
`-- packages/
    `-- shared/
```

## Immediate Next Steps

1. Finalize the planning package.
2. Freeze schema v1 and layer contracts.
3. Convert the MVP into implementation tickets and epics.
4. Bootstrap the implementation stack with the planning guardrails in place.

## Status

Planning and repository foundation.
