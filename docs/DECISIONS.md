# Decisions Log

## D-001: AI-First, Human-Assisted Product Direction

Decision:

- MangAI will be designed as an AI-first, human-assisted workflow rather than full automation.

Reason:

- quality and trust are more important than removing every manual action

## D-002: Project State Is The Source Of Truth

Decision:

- the canonical project state will live in structured app data, not in PSD files

Reason:

- exports must be reproducible and editable without corrupting the main project state

## D-003: PSD Export Is First-Class

Decision:

- PSD export will be treated as a core feature from the start

Reason:

- Photoshop compatibility is central to the target workflow

## D-004: Desktop-First MVP

Decision:

- the MVP editor will prioritize desktop usage

Reason:

- the main workflows require dense controls and visual precision

## D-005: Planning Before Full Bootstrap

Decision:

- the project will complete detailed product and technical planning before major implementation begins

Reason:

- this product has high UX and architecture risk if built too quickly without clear contracts

## D-006: Rust Is Allowed For Focused Acceleration, Not As Default Product Runtime

Decision:

- MangAI may use Rust in focused subsystems where profiling or runtime constraints justify it
- Rust is not the default language for general product implementation

Reason:

- the project benefits more from fast iteration and mature AI tooling first
- Rust should be introduced where it materially improves performance, safety, or systems-level behavior

## D-007: Initial Content Language Scope Is Constrained

Decision:

- initial source-language support is limited to Japanese, Korean, Chinese, and English
- initial target-language support is limited to Portuguese and English

Reason:

- the MVP needs a narrow language matrix to keep OCR, translation, typesetting, QA, and font fallback behavior reliable
