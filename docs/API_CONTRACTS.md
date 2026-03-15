# Layer Contracts

## Goal

Define how `web`, `api`, `workers`, and `shared` interact without duplicating logic or drifting on schema interpretation.

## Localization Contract Rules

- UI locale is a product concern and must not be confused with project source or target language
- language tags in persisted content contracts should use BCP 47
- API error responses should prefer stable `error_code` values over localized prose
- `web` is responsible for localizing UI strings shown to users
- `api` is responsible for validating language and locale fields
- `workers` must consume normalized language metadata only
- the initial supported UI locale pair is `en-US` and `pt-BR`

## Layer Responsibilities

### `packages/shared`

Owns:

- canonical schema types
- enums
- validation rules
- shared DTO definitions
- job payload/result contracts

Must not own:

- persistence logic
- framework-specific code
- provider clients

### `apps/web`

Owns:

- presentation state
- editor interactions
- optimistic UI only where safe
- request composition against API contracts

Must not own:

- business rules that define canonical validity
- worker payload generation directly
- direct database knowledge

### `services/api`

Owns:

- authentication and authorization
- request validation
- persistence
- orchestration of jobs
- mutation rules
- response shaping for web

Must not own:

- heavy compute
- canvas/editor logic
- provider-specific long-running execution

### `services/workers`

Owns:

- execution of long-running jobs
- provider adapter invocation
- deterministic transformation of job payloads into results

Must not own:

- user authentication
- direct web-facing contract shaping
- ad hoc schema variants

## Allowed Write Paths

- `web -> api`
- `api -> database`
- `api -> queue`
- `workers -> api-owned persistence path or job-result persistence contract`

Workers must not mutate unrelated entities directly.

## Request/Response Contract Families

### Project Contracts

#### Create Project Request

```json
{
  "name": "My Project",
  "source_language": "ja-JP",
  "target_language": "en-US",
  "target_text_direction": "ltr"
}
```

#### Create Project Response

```json
{
  "project": {
    "id": "uuid",
    "schema_version": 1,
    "name": "My Project",
    "status": "draft",
    "source_language": "ja-JP",
    "target_language": "en-US",
    "target_text_direction": "ltr"
  }
}
```

### Page Upload Contracts

#### Upload Page Response

```json
{
  "page": {
    "id": "uuid",
    "project_id": "uuid",
    "status": "uploaded",
    "original_asset_id": "uuid"
  }
}
```

### Region Contracts

#### List Regions Response

```json
{
  "regions": [
    {
      "id": "uuid",
      "page_id": "uuid",
      "type": "speech_balloon",
      "state": "draft",
      "origin": "detected",
      "confidence": 0.92,
      "bounding_box": {
        "x": 10,
        "y": 10,
        "width": 100,
        "height": 80
      }
    }
  ]
}
```

#### Update Region Request

```json
{
  "type": "speech_balloon",
  "state": "reviewed",
  "bounding_box": {
    "x": 10,
    "y": 10,
    "width": 100,
    "height": 80
  },
  "shape": {
    "type": "polygon",
    "points": [
      { "x": 10, "y": 10 }
    ]
  }
}
```

### Dialogue Contracts

#### Create Manual Dialogue Request

```json
{
  "page_id": "uuid",
  "content": "text",
  "source_language": "ja-JP",
  "reading_order": 1
}
```

### Translation Contracts

#### Upsert Translation Request

```json
{
  "dialogue_id": "uuid",
  "target_language": "en-US",
  "text_direction": "ltr",
  "content": "translated text",
  "status": "reviewed"
}
```

### Assignment Contracts

#### Upsert Assignment Request

```json
{
  "dialogue_id": "uuid",
  "region_id": "uuid",
  "origin": "manual",
  "approved": true
}
```

### Text Placement Contracts

#### Upsert Placement Request

```json
{
  "assignment_id": "uuid",
  "text_box": {
    "x": 10,
    "y": 10,
    "width": 150,
    "height": 100
  },
  "style": {
    "font_family": "Anime Ace",
    "font_fallbacks": ["Noto Sans", "Arial Unicode MS"],
    "font_size": 24,
    "leading": 28,
    "tracking": 0,
    "alignment": "center",
    "direction": "ltr",
    "rotation": 0,
    "fill": "#000000"
  }
}
```

## Job Contracts

## Orchestration Rule

`api` creates jobs, `workers` execute jobs, and `api` remains the source of truth for status exposure.

### Detect Regions Job

#### Payload

```json
{
  "job_id": "uuid",
  "page_id": "uuid",
  "asset_id": "uuid"
}
```

#### Result

```json
{
  "page_id": "uuid",
  "regions_created": 5,
  "overlay_asset_id": "uuid"
}
```

### Cleanup Job

#### Payload

```json
{
  "job_id": "uuid",
  "page_id": "uuid",
  "source_asset_id": "uuid",
  "region_ids": ["uuid"],
  "mask_revision_ids": ["uuid"]
}
```

#### Result

```json
{
  "page_id": "uuid",
  "cleaned_asset_id": "uuid",
  "variant_asset_ids": ["uuid"]
}
```

### OCR Job

#### Payload

```json
{
  "job_id": "uuid",
  "page_id": "uuid",
  "asset_id": "uuid",
  "region_ids": ["uuid"]
}
```

#### Result

```json
{
  "page_id": "uuid",
  "dialogue_ids": ["uuid"]
}
```

### Translation Job

#### Payload

```json
{
  "job_id": "uuid",
  "project_id": "uuid",
  "dialogue_ids": ["uuid"],
  "source_language": "ja-JP",
  "target_language": "en-US"
}
```

#### Result

```json
{
  "project_id": "uuid",
  "translation_ids": ["uuid"]
}
```

### Matching Job

#### Payload

```json
{
  "job_id": "uuid",
  "page_id": "uuid",
  "dialogue_ids": ["uuid"],
  "region_ids": ["uuid"]
}
```

#### Result

```json
{
  "page_id": "uuid",
  "assignment_ids": ["uuid"]
}
```

### Typesetting Job

#### Payload

```json
{
  "job_id": "uuid",
  "page_id": "uuid",
  "assignment_ids": ["uuid"],
  "style_preset_id": null
}
```

#### Result

```json
{
  "page_id": "uuid",
  "text_placement_ids": ["uuid"]
}
```

### Export Job

#### Payload

```json
{
  "job_id": "uuid",
  "project_id": "uuid",
  "format": "psd",
  "page_ids": ["uuid"]
}
```

#### Result

```json
{
  "project_id": "uuid",
  "format": "psd",
  "output_asset_id": "uuid"
}
```

## Shared Package Initial Ownership

The first version of `packages/shared` should contain:

- enums for schema v1
- DTO types for API contracts
- DTO types for job payloads and results
- validation helpers
- schema version constant

## Non-Negotiable Contract Rules

- `web` never invents enum values
- `workers` never return undocumented fields
- `api` never persists payloads that fail shared validation
- breaking schema changes require a version increment
- locale-sensitive fields must be normalized before persistence
