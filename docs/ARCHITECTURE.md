# Architecture

## Architectural Principle

Store project truth in app-native structured data and generate deliverables from that state.

## Main Components

### Web App

- project dashboard
- upload and asset review
- page editor
- job monitoring
- export management

### API

- auth and project APIs
- asset metadata APIs
- editor state APIs
- job orchestration APIs
- export APIs

### Workers

- detection worker
- cleanup worker
- OCR worker
- translation worker
- export worker

### Persistence

- Postgres for relational data
- object storage for images, masks, and exports
- Redis for queueing and transient job state

## Core Domain Objects

- `Project`
- `Page`
- `Asset`
- `Region`
- `Dialogue`
- `Translation`
- `TextPlacement`
- `ExportJob`

## Processing Pipeline

1. Ingest image assets.
2. Detect candidate text regions.
3. Refine masks.
4. Clean or reconstruct art.
5. Extract or import text.
6. Match text to targets.
7. Apply typesetting.
8. Render exports.

## Editor Responsibilities

- display original and cleaned art
- show region overlays
- allow mask correction
- allow text reassignment
- allow text layout editing
- preview export output

## Export Responsibilities

- layered PSD generation
- flattened JPG generation
- multi-page PDF generation
- batch export status and retry handling
