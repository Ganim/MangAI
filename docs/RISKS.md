# Risks

## Product Risks

### Cleanup Quality

Risk:

- cleanup may damage line art or invent inconsistent background details

Mitigation:

- require mask review
- support variant generation
- keep original and cleaned comparison visible

### Dialogue Assignment Errors

Risk:

- the system may match the wrong line to the wrong balloon

Mitigation:

- explicit assignment review step
- unresolved state instead of forced matching
- reading-order heuristics with manual override

### Weak Typesetting

Risk:

- text may technically fit but still look amateurish

Mitigation:

- strong style presets
- balloon-aware heuristics
- manual adjustment controls

### PSD Export Disappointment

Risk:

- exported PSD may not match expectations for editability

Mitigation:

- define PSD requirements early
- validate against real Photoshop workflows
- treat export as a product surface, not a final afterthought

## Technical Risks

### Provider Lock-In

Risk:

- cleanup or translation quality becomes tied to one external provider

Mitigation:

- provider abstraction layer
- standardized internal job contracts

### Long-Running Job Complexity

Risk:

- background jobs become hard to reason about or retry safely

Mitigation:

- explicit job state machine
- immutable outputs where possible
- idempotent worker behavior

### Schema Drift

Risk:

- frontend, backend, and workers interpret project state differently

Mitigation:

- shared schema contracts
- schema versioning
- compatibility checks in CI

### Editor Complexity

Risk:

- the editor becomes powerful but difficult to use

Mitigation:

- mode clarity
- progressive disclosure
- keep MVP workflows narrow
