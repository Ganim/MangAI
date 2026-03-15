# Planning Review

## Overall Assessment

The planning base is strong enough to start architecture work, but not yet strong enough to begin full implementation safely.

Current planning quality:

- product direction: strong
- workflow definition: good
- architecture direction: good
- executable technical detail: incomplete
- delivery readiness: partial

## Main Strengths

### 1. Correct Product Direction

The product is positioned as AI-first and human-assisted rather than fully automatic.

Why this is strong:

- it aligns with the real reliability limits of cleanup, OCR, matching, and typesetting
- it reduces trust risk
- it preserves professional workflows instead of replacing them poorly

### 2. Source Of Truth Is Not The PSD

The planning correctly treats structured project state as the canonical source.

Why this is strong:

- exports become reproducible
- editor state can evolve independently of export format
- the system avoids coupling business logic to Photoshop internals

### 3. Human Review Is Present In The Right Places

The review loop appears in the highest-risk stages:

- mask correction
- cleanup review
- OCR correction
- dialogue assignment
- final typesetting

Why this is strong:

- these are exactly the areas where quality failures would damage trust

### 4. The Planning Already Separates Domain Concerns Well

The existing docs already distinguish:

- assets
- regions
- dialogue
- translation
- placement
- exports

Why this is strong:

- this reduces the chance of building a monolithic editor model too early

### 5. The Planning Is Honest About Risks

The documentation already acknowledges:

- cleanup uncertainty
- assignment ambiguity
- weak typography risk
- PSD export risk

Why this is strong:

- teams usually fail when those risks stay implicit

## Main Weaknesses

### 1. Missing Explicit State Machines

The planning names statuses, but does not yet define exact allowed states and transitions for:

- project
- page
- region
- dialogue
- jobs
- exports

Why this matters:

- without state machines, retries and edge cases turn inconsistent quickly

### 2. Domain Objects Are Defined, But Not Yet Contracted

The domain model explains concepts, but does not yet define:

- required vs optional fields
- enum values
- versioning rules
- ownership rules
- invariants

Why this matters:

- web, api, workers, and shared will drift without precise contracts

### 3. The Asset Lifecycle Is Still Underdefined

The docs describe assets, but not the rules for:

- which assets are immutable
- which assets are derived
- how variants are retained
- how active outputs are selected

Why this matters:

- cleanup and export systems can become difficult to debug without explicit asset lineage

### 4. API Boundaries Are Implied, Not Specified

The architecture says there will be web, api, workers, and shared, but it does not yet define:

- which layer owns validation
- which layer owns orchestration
- which layer is allowed to write which entities
- what workers receive as input

Why this matters:

- this is where duplicated logic and cross-layer conflicts usually begin

### 5. UX Planning Is Good, But Not Yet Operational

The editor UX is described, but still lacks:

- exact mode switching rules
- autosave semantics
- conflict behavior during async job completion
- disabled states while jobs run

Why this matters:

- the editor is the most failure-prone part of the product

### 6. Quality Standards Need Enforcement Hooks

The quality doc says the right things, but it does not yet map them to:

- required test owners
- CI gates
- schema checks
- code ownership boundaries

Why this matters:

- quality policy without enforcement becomes aspirational only

## Highest-Priority Improvements

### 1. Define Schema V1

This is the most important next step.

It should define:

- entities
- enums
- required fields
- active revision rules
- versioning
- canonical JSON examples

### 2. Define Cross-Layer Contracts

This should specify:

- what `web` reads and writes
- what `api` validates and persists
- what `workers` are allowed to consume and emit
- what `shared` owns

### 3. Convert MVP Into Sequenced Epics And Tickets

This should prevent:

- building low-value infrastructure first
- blocking critical product flows behind nonessential work

### 4. Add Explicit State Rules

These can live in schema and API contract docs.

Minimum required state machines:

- page
- region
- dialogue
- job
- export

## Build Readiness Verdict

The project is ready for:

- schema design
- API contract definition
- backlog sequencing
- monorepo bootstrapping based on those contracts

The project is not yet ready for:

- full implementation of editor behavior
- worker orchestration
- export logic

until schema and contract documents are finished.
