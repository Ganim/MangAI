# Quality Standards

## Product Quality Principles

- preserve original inputs
- keep every destructive operation reversible
- prefer explicit state over hidden side effects
- optimize for debuggability

## Code Quality

- strict boundaries between app, api, workers, and shared contracts
- no UI-only types duplicated in backend contracts
- no direct worker writes that bypass domain rules
- all important asynchronous jobs must be idempotent

## Testing Strategy

### Unit Tests

- geometry helpers
- text fitting logic
- assignment heuristics
- schema validation
- locale and language normalization

### Integration Tests

- upload to page creation
- detection job persistence
- cleanup job lifecycle
- export job lifecycle

### End-to-End Tests

- create project
- upload page
- review regions
- assign dialogue
- export output
- verify at least one alternate UI locale

## Reliability Standards

- async jobs must expose status transitions
- every job failure must include a user-safe message and internal debug context
- retries must not duplicate business entities unexpectedly
- editor autosave must be resilient to refreshes

## Observability

- structured logs
- job timing metrics
- provider latency metrics
- export failure metrics

## UX Quality Checks

- every AI suggestion has visible confidence or status
- every important action provides feedback
- every error state provides recovery options
- preview should reflect export output as closely as possible
- app UI should remain usable in supported locales without broken layout

## Done Criteria For Features

A feature is not done until:

- the happy path works
- the main failure cases are handled
- persistence is stable
- at least one test layer exists
- user recovery is defined
