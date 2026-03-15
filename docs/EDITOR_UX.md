# Editor UX

## UX Principles

- the editor should feel trustworthy before it feels magical
- AI suggestions must be easy to override
- users should never lose track of what is original, suggested, or approved
- the shortest path for common corrections should be obvious

## Main Editor Layout

### Left Panel

- page list
- region list
- dialogue list
- filter controls

### Center Canvas

- original/cleaned page viewer
- overlay mode switch
- region handles
- mask editing interactions
- text placement bounding boxes

### Right Panel

- selected region details
- selected dialogue details
- translation text
- typesetting controls
- action buttons

## Primary Modes

- review regions
- edit masks
- review text
- assign dialogue
- typeset
- compare output

## Required UX States

- loading
- processing
- partial failure
- dirty unsaved changes
- approved result
- retry available

## Key Interactions

### Region Review

- select region
- toggle visibility
- delete false positive
- add missing region

### Mask Editing

- drag handles
- paint erase
- paint add
- reset to detected mask

### Dialogue Review

- edit OCR result
- paste manual text
- reorder lines
- mark unresolved

### Assignment Review

- drag dialogue to region
- click reassign
- show unmatched items

### Typesetting

- resize text box
- adjust font size
- change alignment
- tweak line breaks
- apply preset

## UX Risks To Avoid

- too many hidden modes
- editor state that changes without clear feedback
- AI actions that overwrite manual edits
- export that looks different from the editor preview
