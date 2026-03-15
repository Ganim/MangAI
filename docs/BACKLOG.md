# MVP Backlog

## Execution Rules

- tickets are ordered by dependency, not by convenience
- no editor polish work should start before state contracts exist
- no worker implementation should start before job contracts exist

## Epic 1: Foundation Contracts

### E1-T1 Define schema v1

Deliverable:

- shared schema document and initial schema files

Done when:

- all core entities and enums are frozen for v1

### E1-T2 Define API contracts

Deliverable:

- request and response contracts for project, page, region, dialogue, jobs, and export flows

Done when:

- web and api can implement from the same contract

### E1-T3 Define worker job contracts

Deliverable:

- payload and result contracts for detection, cleanup, OCR, translation, matching, typesetting, and export

Done when:

- api and workers agree on payload ownership and outputs

## Epic 2: Repository And Tooling Bootstrap

### E2-T1 Bootstrap `packages/shared`

- add schema source files
- add enum exports
- add validation layer

### E2-T2 Bootstrap `services/api`

- FastAPI app shell
- health route
- config loading
- base routing structure

### E2-T3 Bootstrap `services/workers`

- worker app shell
- queue config
- job runner structure

### E2-T4 Bootstrap `apps/web`

- Next.js app shell
- auth placeholder
- project dashboard shell

## Epic 3: Project And Upload Flow

### E3-T1 Project creation API

### E3-T2 Project list and detail page

### E3-T3 Asset upload endpoint

### E3-T4 Page creation from uploaded assets

### E3-T5 Upload UI

Done when:

- a user can create a project and upload pages end-to-end

## Epic 4: Detection And Region Review

### E4-T1 Detection job orchestration

### E4-T2 Detection worker adapter

### E4-T3 Region persistence

### E4-T4 Overlay generation

### E4-T5 Page editor overlay view

### E4-T6 Manual region add/remove/edit

Done when:

- a user can review and correct detection results

## Epic 5: Mask Revision And Cleanup

### E5-T1 Mask revision model and endpoints

### E5-T2 Cleanup job orchestration

### E5-T3 Cleanup worker adapter

### E5-T4 Cleanup asset versioning

### E5-T5 Before/after compare UI

### E5-T6 Retry and variant flow

Done when:

- a user can generate and approve cleaned art

## Epic 6: OCR And Dialogue Intake

### E6-T1 OCR job orchestration

### E6-T2 OCR worker adapter

### E6-T3 Dialogue persistence

### E6-T4 OCR review UI

### E6-T5 Manual text input and edit UI

Done when:

- source dialogue exists as structured editable state

## Epic 7: Translation And Matching

### E7-T1 Translation draft generation

### E7-T2 Translation review UI

### E7-T3 Matching heuristics

### E7-T4 Assignment API

### E7-T5 Assignment review UI

Done when:

- each line can be assigned and reviewed

## Epic 8: Typesetting

### E8-T1 Text placement model

### E8-T2 Typesetting heuristics

### E8-T3 Placement generation job

### E8-T4 Canvas text controls

### E8-T5 Style preset model

Done when:

- auto layout works and is editable

## Epic 9: Export

### E9-T1 Export validation rules

### E9-T2 JPG renderer

### E9-T3 PSD renderer

### E9-T4 Export UI and download flow

Done when:

- a project can export usable JPG and PSD outputs

## Epic 10: Quality Gates

### E10-T1 Shared schema validation tests

### E10-T2 API integration tests

### E10-T3 Worker contract tests

### E10-T4 End-to-end happy path test

### E10-T5 Logging and job metrics baseline

## Recommended First Sprint

The first implementation sprint should contain only:

- E1-T1
- E1-T2
- E1-T3
- E2-T1
- E2-T2
- E2-T3
- E2-T4

This keeps the first sprint focused on contracts and scaffolding instead of accidental feature work.
