# MVP Definition

## MVP Goal

Prove that MangAI can reduce the time needed to clean, translate, and typeset comic pages while preserving user control and Photoshop compatibility.

## Included

- project creation
- page upload
- page list view
- multilingual-ready UI architecture
- initial UI locales: `en-US` and `pt-BR`
- text region detection
- manual region and mask correction
- AI cleanup on selected regions
- before/after page comparison
- OCR text extraction
- manual source text editing
- manual or AI-assisted translation input
- dialogue-to-region assignment review
- automatic typesetting for standard balloons
- manual layout adjustments
- JPG export
- PSD export

## Explicitly Excluded

- team collaboration
- real-time multi-user editing
- billing
- permissions system
- translation memory
- glossary enforcement
- advanced SFX handling
- complex chapter management
- mobile-first editing

## MVP Constraints

- support single-user workflows first
- optimize for desktop browsers
- prioritize manga/comic balloons before free-form text over scenery
- prefer reliability and editability over aggressive automation
- treat internationalization as a foundation concern, not a late-stage enhancement
- focus first-class UX and typesetting support on English and Portuguese

## MVP Success Criteria

- user can finish a page end-to-end in one product
- user can fix any incorrect AI decision in the editor
- export output is usable in Photoshop
- core workflow does not require command line access

## MVP Quality Bar

- no destructive overwrite of original assets
- every AI result is reviewable
- every important entity is persisted in structured state
- retries are possible without manual database cleanup

## MVP Exit Definition

MVP is complete when a user can:

1. upload a page
2. detect and review regions
3. clean the page
4. extract or enter text
5. assign translated text to balloons
6. adjust typesetting
7. export a usable PSD and JPG
