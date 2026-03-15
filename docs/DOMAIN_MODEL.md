# Domain Model

## Principles

- store product truth in explicit entities
- prefer immutable job outputs and mutable editor state
- separate source text from translated text
- separate region geometry from text placement geometry

## Core Entities

### Project

Represents a user workspace for a chapter, one-shot, or test batch.

Key fields:

- `id`
- `name`
- `owner_id`
- `status`
- `default_style_preset_id`
- `created_at`
- `updated_at`

### Page

Represents one page inside a project.

Key fields:

- `id`
- `project_id`
- `index`
- `original_asset_id`
- `cleaned_asset_id`
- `width`
- `height`
- `status`

### Asset

Represents a stored binary file.

Key fields:

- `id`
- `project_id`
- `page_id`
- `kind`
- `storage_key`
- `mime_type`
- `width`
- `height`
- `metadata_json`

Kinds may include:

- original
- overlay
- mask
- cleaned
- export

### Region

Represents a user-visible target area on a page.

Key fields:

- `id`
- `page_id`
- `type`
- `shape_json`
- `bounding_box_json`
- `confidence`
- `origin`
- `state`

Types may include:

- speech_balloon
- narration_box
- free_text
- sfx
- unknown

Origins may include:

- detected
- user_created
- merged

### MaskRevision

Represents an editable cleanup mask state for a region.

Key fields:

- `id`
- `region_id`
- `version`
- `mask_shape_json`
- `approved`
- `created_by`
- `created_at`

### Dialogue

Represents a text unit that may be OCR-derived or manually entered.

Key fields:

- `id`
- `page_id`
- `source`
- `source_language`
- `content`
- `reading_order`
- `status`

Sources may include:

- ocr
- manual
- imported_script

### Translation

Represents a translated form of a dialogue line.

Key fields:

- `id`
- `dialogue_id`
- `target_language`
- `provider`
- `content`
- `status`
- `edited_by_user`

### Assignment

Represents the mapping of dialogue to region.

Key fields:

- `id`
- `page_id`
- `dialogue_id`
- `region_id`
- `confidence`
- `origin`
- `approved`

### TextPlacement

Represents how translated text is visually placed.

Key fields:

- `id`
- `assignment_id`
- `text_box_json`
- `font_family`
- `font_size`
- `leading`
- `tracking`
- `alignment`
- `rotation`
- `style_json`

### ExportJob

Represents an export request.

Key fields:

- `id`
- `project_id`
- `format`
- `scope`
- `status`
- `asset_id`
- `error_message`

## Relationships

- one `Project` has many `Page`
- one `Page` has many `Region`
- one `Page` has many `Dialogue`
- one `Dialogue` has many `Translation`
- one `Assignment` maps one `Dialogue` to one `Region`
- one `Assignment` has one active `TextPlacement`

## State Model Notes

- original assets are never mutated
- cleanup outputs are versioned assets
- editor state should point to active revisions
- exports must be reproducible from persisted state
