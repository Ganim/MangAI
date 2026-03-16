from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path

from mangai_workers.runner import WorkerExecutionError


@dataclass(frozen=True)
class DetectedRegionCandidate:
    type: str
    confidence: float
    bounding_box: dict[str, float]


def detect_regions_from_asset(
    *,
    asset_path: Path,
    page_width: int,
    page_height: int,
) -> list[DetectedRegionCandidate]:
    if not asset_path.exists():
        raise WorkerExecutionError(f"Could not find source asset '{asset_path}'.")

    asset_bytes = asset_path.read_bytes()
    if len(asset_bytes) == 0:
        raise WorkerExecutionError(f"Source asset '{asset_path}' is empty.")

    digest = hashlib.sha256(asset_bytes).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    region_count = 2 + (digest[8] % 2)
    portrait_bias = page_height >= page_width

    candidates: list[DetectedRegionCandidate] = []
    attempts = 0
    while len(candidates) < region_count and attempts < region_count * 10:
        attempts += 1
        region_type = _pick_region_type(rng, portrait_bias)
        width_ratio, height_ratio = _pick_region_size_ratios(rng, region_type, portrait_bias)
        box_width = max(round(page_width * width_ratio, 2), 48.0)
        box_height = max(round(page_height * height_ratio, 2), 36.0)
        max_x = max(page_width - box_width, 0.0)
        max_y = max(page_height - box_height, 0.0)
        x = round(rng.uniform(0, max_x), 2)
        y = round(rng.uniform(0, max_y), 2)
        bounding_box = {
            "x": x,
            "y": y,
            "width": box_width,
            "height": box_height,
        }

        if _overlaps_existing(candidates, bounding_box):
            continue

        confidence = round(0.76 + (rng.random() * 0.2), 2)
        candidates.append(
            DetectedRegionCandidate(
                type=region_type,
                confidence=min(confidence, 0.98),
                bounding_box=bounding_box,
            )
        )

    if len(candidates) == 0:
        candidates.append(
            DetectedRegionCandidate(
                type="speech_balloon",
                confidence=0.8,
                bounding_box={
                    "x": round(page_width * 0.18, 2),
                    "y": round(page_height * 0.14, 2),
                    "width": round(page_width * 0.3, 2),
                    "height": round(page_height * 0.16, 2),
                },
            )
        )

    return candidates


def _pick_region_type(rng: random.Random, portrait_bias: bool) -> str:
    options = ["speech_balloon", "speech_balloon", "speech_balloon", "narration_box", "free_text"]
    if not portrait_bias:
        options.append("free_text")
    return options[rng.randrange(0, len(options))]


def _pick_region_size_ratios(
    rng: random.Random,
    region_type: str,
    portrait_bias: bool,
) -> tuple[float, float]:
    if region_type == "narration_box":
        return (rng.uniform(0.18, 0.3), rng.uniform(0.08, 0.14))
    if region_type == "free_text":
        return (rng.uniform(0.16, 0.24), rng.uniform(0.08, 0.12))
    if portrait_bias:
        return (rng.uniform(0.22, 0.34), rng.uniform(0.12, 0.18))
    return (rng.uniform(0.18, 0.28), rng.uniform(0.14, 0.2))


def _overlaps_existing(
    candidates: list[DetectedRegionCandidate],
    bounding_box: dict[str, float],
) -> bool:
    for candidate in candidates:
        existing = candidate.bounding_box
        overlaps_horizontally = (
            bounding_box["x"] < existing["x"] + existing["width"]
            and bounding_box["x"] + bounding_box["width"] > existing["x"]
        )
        overlaps_vertically = (
            bounding_box["y"] < existing["y"] + existing["height"]
            and bounding_box["y"] + bounding_box["height"] > existing["y"]
        )
        if overlaps_horizontally and overlaps_vertically:
            return True
    return False
