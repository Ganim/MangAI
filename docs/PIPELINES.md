# Pipelines

## Design Principles

- every pipeline stage produces explicit output
- every expensive stage runs asynchronously
- every AI output must be reviewable
- retries should not corrupt prior state

## Detection Pipeline

### Input

- original page asset

### Output

- region candidates
- overlay asset
- confidence metadata

### Steps

1. normalize image metadata
2. run detection model
3. classify region type
4. persist regions
5. render overlay preview

## Cleanup Pipeline

### Input

- original page asset
- approved region masks

### Output

- cleaned asset candidate
- optional variant assets
- per-region processing metadata

### Steps

1. extract per-region masks
2. choose cleanup strategy by region type
3. run localized cleanup
4. stitch page output
5. store preview and metadata

### Strategy Notes

- speech balloons should favor conservative cleanup
- free text over scenery may require stronger inpainting
- difficult regions may produce multiple variants

## OCR Pipeline

### Input

- page asset
- active regions

### Output

- dialogue candidates
- OCR confidence metadata

### Steps

1. sort candidate regions
2. crop input by region
3. run OCR
4. normalize output
5. persist editable dialogue candidates

## Translation Pipeline

### Input

- approved source dialogue
- project language settings

### Output

- translation drafts

### Steps

1. prepare dialogue batch
2. inject project context
3. request translation
4. persist drafts
5. mark items for review

## Matching Pipeline

### Input

- approved regions
- source dialogue or translations

### Output

- proposed assignments

### Steps

1. estimate reading order
2. compare dialogue sequence to region sequence
3. assign by confidence
4. store unresolved items

## Typesetting Pipeline

### Input

- approved assignments
- target text
- region geometry
- style preset

### Output

- editable text placement
- layout metrics

### Steps

1. determine text box area
2. estimate font size bounds
3. generate line breaks
4. apply spacing heuristics
5. persist placement for manual adjustment

## Export Pipeline

### Input

- approved page state

### Output

- JPG
- PSD
- PDF later in the roadmap

### Steps

1. validate project completeness
2. render layer plan
3. render output assets
4. persist export files
5. expose download links
