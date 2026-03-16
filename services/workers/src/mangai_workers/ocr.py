from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OcrCandidateRegion:
    id: str
    type: str
    confidence: float | None
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class OcrLine:
    region_id: str
    text: str
    confidence: float


OCR_FALLBACK_TEMPLATES = {
    "ja": "テキスト {index}",
    "ko": "텍스트 {index}",
    "zh": "文本 {index}",
    "en": "Text line {index}",
}


def extract_ocr_lines_from_asset(
    *,
    asset_path: Path,
    source_language: str,
    regions: list[OcrCandidateRegion],
) -> list[OcrLine]:
    if not asset_path.exists():
        raise FileNotFoundError(f"Could not find OCR source asset '{asset_path}'.")

    ordered_regions = sorted(regions, key=lambda candidate: (candidate.y, candidate.x, candidate.id))
    template = OCR_FALLBACK_TEMPLATES.get(source_language.split("-", 1)[0].lower(), "Text line {index}")

    return [
        OcrLine(
            region_id=region.id,
            text=template.format(index=index),
            confidence=round(region.confidence if region.confidence is not None else 0.68, 2),
        )
        for index, region in enumerate(ordered_regions, start=1)
    ]
