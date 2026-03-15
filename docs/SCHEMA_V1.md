# Schema V1

## Purpose

Schema V1 defines the canonical project state that all layers must understand consistently.

This schema is product-facing, not database-specific.

## Global Rules

- all IDs are UUID strings
- all timestamps use ISO 8601 UTC
- original assets are immutable
- derived assets are versioned
- every persisted object has `id`, `created_at`, and `updated_at`
- every stateful entity uses explicit enums

## Enumerations

### ProjectStatus

- `draft`
- `active`
- `archived`

### PageStatus

- `uploaded`
- `analyzed`
- `cleanup_ready`
- `cleaned`
- `text_ready`
- `typeset_ready`
- `export_ready`
- `error`

### RegionType

- `speech_balloon`
- `narration_box`
- `free_text`
- `sfx`
- `unknown`

### RegionOrigin

- `detected`
- `user_created`
- `user_split`
- `user_merged`

### RegionState

- `draft`
- `reviewed`
- `approved`
- `rejected`

### DialogueSource

- `ocr`
- `manual`
- `imported_script`

### DialogueStatus

- `draft`
- `reviewed`
- `approved`
- `rejected`

### TranslationStatus

- `draft`
- `reviewed`
- `approved`

### AssignmentOrigin

- `automatic`
- `manual`

### JobType

- `detect_regions`
- `generate_cleanup`
- `run_ocr`
- `generate_translation`
- `match_dialogue`
- `generate_typesetting`
- `export_project`

### JobStatus

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

### ExportFormat

- `jpg`
- `psd`
- `pdf`

### AssetKind

- `original`
- `overlay`
- `mask`
- `cleaned`
- `cleanup_variant`
- `ocr_preview`
- `export`

## Shared Value Objects

### BoundingBox

```json
{
  "x": 0,
  "y": 0,
  "width": 0,
  "height": 0
}
```

### PolygonShape

```json
{
  "type": "polygon",
  "points": [
    { "x": 0, "y": 0 }
  ]
}
```

### TextStyle

```json
{
  "font_family": "string",
  "font_size": 24,
  "leading": 28,
  "tracking": 0,
  "alignment": "center",
  "rotation": 0,
  "fill": "#000000"
}
```

## Canonical Entities

### Project

```json
{
  "id": "uuid",
  "schema_version": 1,
  "name": "My Project",
  "owner_id": "uuid",
  "status": "draft",
  "source_language": "ja",
  "target_language": "en",
  "default_style_preset_id": null,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Required fields:

- `id`
- `schema_version`
- `name`
- `owner_id`
- `status`
- `source_language`
- `target_language`

### Page

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "index": 1,
  "status": "uploaded",
  "original_asset_id": "uuid",
  "active_cleaned_asset_id": null,
  "width": 2480,
  "height": 3508,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- `index` must be unique within a project
- `original_asset_id` must point to an immutable `original` asset

### Asset

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "page_id": "uuid",
  "kind": "original",
  "storage_key": "projects/p1/pages/page-1/original.png",
  "mime_type": "image/png",
  "width": 2480,
  "height": 3508,
  "is_active": true,
  "derived_from_asset_id": null,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- `original` assets can never be replaced
- derived assets should reference `derived_from_asset_id` when applicable
- only one active cleaned asset should exist per page per output slot

### Region

```json
{
  "id": "uuid",
  "page_id": "uuid",
  "type": "speech_balloon",
  "origin": "detected",
  "state": "draft",
  "confidence": 0.94,
  "bounding_box": {
    "x": 100,
    "y": 120,
    "width": 320,
    "height": 220
  },
  "shape": {
    "type": "polygon",
    "points": [
      { "x": 100, "y": 120 },
      { "x": 420, "y": 120 },
      { "x": 420, "y": 340 },
      { "x": 100, "y": 340 }
    ]
  },
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- `confidence` is optional for manual regions and required for detected ones
- `state=approved` means it can be used by downstream jobs

### MaskRevision

```json
{
  "id": "uuid",
  "region_id": "uuid",
  "version": 1,
  "is_active": true,
  "approved": true,
  "shape": {
    "type": "polygon",
    "points": [
      { "x": 100, "y": 120 }
    ]
  },
  "created_by": "uuid",
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- only one active mask revision per region
- prior revisions are immutable once superseded

### Dialogue

```json
{
  "id": "uuid",
  "page_id": "uuid",
  "source": "ocr",
  "source_language": "ja",
  "content": "....",
  "reading_order": 1,
  "status": "draft",
  "source_region_id": "uuid",
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- `source_region_id` is optional but recommended for OCR-generated dialogue
- `reading_order` must be unique per page among active dialogue records

### Translation

```json
{
  "id": "uuid",
  "dialogue_id": "uuid",
  "target_language": "en",
  "provider": "manual",
  "content": "I can handle this.",
  "status": "draft",
  "edited_by_user": true,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- approved exports should use only approved translations
- multiple translations may exist, but only one active approved translation should be exportable

### Assignment

```json
{
  "id": "uuid",
  "page_id": "uuid",
  "dialogue_id": "uuid",
  "region_id": "uuid",
  "origin": "automatic",
  "confidence": 0.83,
  "approved": false,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- a dialogue may be unassigned during editing
- final export requires all exportable dialogue to have an approved assignment

### TextPlacement

```json
{
  "id": "uuid",
  "assignment_id": "uuid",
  "is_active": true,
  "text_box": {
    "x": 120,
    "y": 140,
    "width": 280,
    "height": 180
  },
  "style": {
    "font_family": "Anime Ace",
    "font_size": 26,
    "leading": 30,
    "tracking": 0,
    "alignment": "center",
    "rotation": 0,
    "fill": "#000000"
  },
  "layout_metrics": {
    "overflow": false,
    "line_count": 3
  },
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- only one active placement per assignment
- placements are replaceable but previous revisions should remain auditable

### Job

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "page_id": "uuid",
  "type": "detect_regions",
  "status": "queued",
  "payload": {
    "page_id": "uuid"
  },
  "result": null,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

Rules:

- jobs are append-only execution records
- retries should create new jobs unless the orchestration layer explicitly supports resumable execution

### ExportJob

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "format": "psd",
  "scope": {
    "page_ids": ["uuid"]
  },
  "status": "queued",
  "output_asset_id": null,
  "error_message": null,
  "created_at": "2026-03-15T00:00:00Z",
  "updated_at": "2026-03-15T00:00:00Z"
}
```

## State Transition Rules

### Page

- `uploaded -> analyzed`
- `analyzed -> cleanup_ready`
- `cleanup_ready -> cleaned`
- `cleaned -> text_ready`
- `text_ready -> typeset_ready`
- `typeset_ready -> export_ready`
- any state -> `error`

### Region

- `draft -> reviewed`
- `reviewed -> approved`
- `reviewed -> rejected`

### Dialogue

- `draft -> reviewed`
- `reviewed -> approved`
- `reviewed -> rejected`

### Job

- `queued -> running`
- `running -> succeeded`
- `running -> failed`
- `queued -> canceled`
- `running -> canceled`

## Ownership Rules

- `web` may create user-intent mutations only through the API
- `api` owns validation and persistence rules
- `workers` may only apply changes defined by job contracts
- `shared` owns schema definitions and enum contracts
