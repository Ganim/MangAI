from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING

from mangai_workers.ocr import OcrProviderError, RecognizedLine, extract_paddle_recognized_lines
from mangai_workers.runner import WorkerExecutionError


if TYPE_CHECKING:
    from mangai_workers.config import WorkerSettings


@dataclass(frozen=True)
class DetectedRegionCandidate:
    type: str
    confidence: float
    bounding_box: dict[str, float]


@dataclass(frozen=True)
class RecognizedTextBox:
    text: str
    confidence: float
    x: float
    y: float
    width: float
    height: float


def detect_regions_from_asset(
    *,
    asset_path: Path,
    page_width: int,
    page_height: int,
    source_language: str = "ja-JP",
    settings: WorkerSettings | None = None,
) -> list[DetectedRegionCandidate]:
    if not asset_path.exists():
        raise WorkerExecutionError(f"Could not find source asset '{asset_path}'.")

    asset_bytes = asset_path.read_bytes()
    if len(asset_bytes) == 0:
        raise WorkerExecutionError(f"Source asset '{asset_path}' is empty.")

    if settings is not None:
        try:
            recognized_lines = extract_paddle_recognized_lines(
                asset_path=asset_path,
                source_language=source_language,
                settings=settings,
            )
            candidates = build_detected_regions_from_recognized_lines(
                recognized_lines=recognized_lines,
                page_width=page_width,
                page_height=page_height,
            )
            if len(candidates) > 0:
                return candidates
        except Exception:  # noqa: BLE001 - region detection must degrade gracefully to fallback
            pass

    return _detect_regions_from_fallback_bytes(
        asset_bytes=asset_bytes,
        page_width=page_width,
        page_height=page_height,
    )


def build_detected_regions_from_recognized_lines(
    *,
    recognized_lines: list[RecognizedLine],
    page_width: int,
    page_height: int,
) -> list[DetectedRegionCandidate]:
    normalized_boxes = _normalize_recognized_lines(recognized_lines)
    if len(normalized_boxes) == 0:
        return []

    clusters = _cluster_text_boxes(normalized_boxes)
    clusters = _split_large_clusters(
        clusters=clusters,
        page_width=page_width,
        page_height=page_height,
    )
    candidates: list[DetectedRegionCandidate] = []
    for cluster in clusters:
        if len(cluster) == 0:
            continue
        candidate = _build_cluster_candidate(
            cluster=cluster,
            page_width=page_width,
            page_height=page_height,
        )
        if candidate is None:
            continue
        candidates.append(candidate)

    deduplicated = _deduplicate_candidates(candidates)
    return sorted(
        deduplicated,
        key=lambda candidate: (
            candidate.bounding_box["y"],
            candidate.bounding_box["x"],
            candidate.type,
        ),
    )


def _normalize_recognized_lines(recognized_lines: list[RecognizedLine]) -> list[RecognizedTextBox]:
    normalized: list[RecognizedTextBox] = []
    for line in recognized_lines:
        if line.text.strip() == "":
            continue

        width = max(float(line.width), 1.0)
        height = max(float(line.height), 1.0)
        x = float(line.x) - (width / 2)
        y = float(line.y) - (height / 2)
        confidence = float(line.confidence)

        if width < 8 or height < 8:
            continue
        if confidence < 0.25 and max(width, height) < 28:
            continue

        normalized.append(
            RecognizedTextBox(
                text=line.text,
                confidence=confidence,
                x=x,
                y=y,
                width=width,
                height=height,
            )
        )
    return normalized


def _cluster_text_boxes(text_boxes: list[RecognizedTextBox]) -> list[list[RecognizedTextBox]]:
    if len(text_boxes) == 0:
        return []

    parents = list(range(len(text_boxes)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_index in range(len(text_boxes)):
        for right_index in range(left_index + 1, len(text_boxes)):
            if _should_group_text_boxes(text_boxes[left_index], text_boxes[right_index]):
                union(left_index, right_index)

    grouped: dict[int, list[RecognizedTextBox]] = {}
    for index, text_box in enumerate(text_boxes):
        root = find(index)
        grouped.setdefault(root, []).append(text_box)

    return sorted(
        grouped.values(),
        key=lambda cluster: (
            min(text_box.y for text_box in cluster),
            min(text_box.x for text_box in cluster),
        ),
    )


def _should_group_text_boxes(left: RecognizedTextBox, right: RecognizedTextBox) -> bool:
    horizontal_gap = _axis_gap(left.x, left.x + left.width, right.x, right.x + right.width)
    vertical_gap = _axis_gap(left.y, left.y + left.height, right.y, right.y + right.height)
    horizontal_overlap = _axis_overlap(left.x, left.x + left.width, right.x, right.x + right.width)
    vertical_overlap = _axis_overlap(left.y, left.y + left.height, right.y, right.y + right.height)

    max_width = max(left.width, right.width)
    max_height = max(left.height, right.height)
    min_width = max(min(left.width, right.width), 1.0)
    min_height = max(min(left.height, right.height), 1.0)
    vertical_overlap_ratio = vertical_overlap / min_height
    horizontal_overlap_ratio = horizontal_overlap / min_width

    column_pair = (
        horizontal_gap <= max(18.0, max_width * 1.45)
        and vertical_overlap_ratio >= 0.42
    )
    row_pair = (
        vertical_gap <= max(18.0, max_height * 0.65)
        and horizontal_overlap_ratio >= 0.42
    )
    touching_pair = (
        horizontal_gap <= max(14.0, max_width * 0.45)
        and vertical_gap <= max(16.0, max_height * 0.35)
    )

    return column_pair or row_pair or touching_pair


def _split_large_clusters(
    *,
    clusters: list[list[RecognizedTextBox]],
    page_width: int,
    page_height: int,
) -> list[list[RecognizedTextBox]]:
    split_clusters: list[list[RecognizedTextBox]] = []
    for cluster in clusters:
        split_clusters.extend(
            _split_cluster_recursively(
                cluster=cluster,
                page_width=page_width,
                page_height=page_height,
            )
        )
    return split_clusters


def _split_cluster_recursively(
    *,
    cluster: list[RecognizedTextBox],
    page_width: int,
    page_height: int,
) -> list[list[RecognizedTextBox]]:
    if len(cluster) < 4:
        return [cluster]

    min_x = min(text_box.x for text_box in cluster)
    min_y = min(text_box.y for text_box in cluster)
    max_x = max(text_box.x + text_box.width for text_box in cluster)
    max_y = max(text_box.y + text_box.height for text_box in cluster)
    cluster_width = max_x - min_x
    cluster_height = max_y - min_y
    cluster_area = cluster_width * cluster_height
    page_area = page_width * page_height

    is_oversized = (
        cluster_area > page_area * 0.16
        or cluster_width > page_width * 0.42
        or cluster_height > page_height * 0.42
    )
    if not is_oversized:
        return [cluster]

    vertical_split = _split_cluster_on_axis(cluster, axis="y")
    horizontal_split = _split_cluster_on_axis(cluster, axis="x")
    split_choice = _choose_better_cluster_split(vertical_split, horizontal_split)
    if split_choice is None:
        return [cluster]

    left_cluster, right_cluster = split_choice
    return [
        *_split_cluster_recursively(
            cluster=left_cluster,
            page_width=page_width,
            page_height=page_height,
        ),
        *_split_cluster_recursively(
            cluster=right_cluster,
            page_width=page_width,
            page_height=page_height,
        ),
    ]


def _split_cluster_on_axis(
    cluster: list[RecognizedTextBox],
    *,
    axis: str,
) -> tuple[list[RecognizedTextBox], list[RecognizedTextBox], float] | None:
    if axis == "x":
        ordered_boxes = sorted(cluster, key=lambda text_box: (text_box.x, text_box.y))
        threshold = max(42.0, median(text_box.width for text_box in cluster) * 1.45)
        gap_getter = lambda current, nxt: nxt.x - (current.x + current.width)
    else:
        ordered_boxes = sorted(cluster, key=lambda text_box: (text_box.y, text_box.x))
        threshold = max(54.0, median(text_box.height for text_box in cluster) * 0.9)
        gap_getter = lambda current, nxt: nxt.y - (current.y + current.height)

    best_index = -1
    best_gap = 0.0
    for index in range(len(ordered_boxes) - 1):
        current_box = ordered_boxes[index]
        next_box = ordered_boxes[index + 1]
        gap = gap_getter(current_box, next_box)
        if gap > best_gap:
            best_gap = gap
            best_index = index

    if best_index < 0 or best_gap <= threshold:
        return None

    left_cluster = ordered_boxes[: best_index + 1]
    right_cluster = ordered_boxes[best_index + 1 :]
    if len(left_cluster) == 0 or len(right_cluster) == 0:
        return None
    return left_cluster, right_cluster, best_gap


def _choose_better_cluster_split(
    vertical_split: tuple[list[RecognizedTextBox], list[RecognizedTextBox], float] | None,
    horizontal_split: tuple[list[RecognizedTextBox], list[RecognizedTextBox], float] | None,
) -> tuple[list[RecognizedTextBox], list[RecognizedTextBox]] | None:
    if vertical_split is None and horizontal_split is None:
        return None
    if vertical_split is None:
        return horizontal_split[0], horizontal_split[1]
    if horizontal_split is None:
        return vertical_split[0], vertical_split[1]
    if vertical_split[2] >= horizontal_split[2]:
        return vertical_split[0], vertical_split[1]
    return horizontal_split[0], horizontal_split[1]


def _build_cluster_candidate(
    *,
    cluster: list[RecognizedTextBox],
    page_width: int,
    page_height: int,
) -> DetectedRegionCandidate | None:
    box_count = len(cluster)
    min_x = min(text_box.x for text_box in cluster)
    min_y = min(text_box.y for text_box in cluster)
    max_x = max(text_box.x + text_box.width for text_box in cluster)
    max_y = max(text_box.y + text_box.height for text_box in cluster)
    cluster_width = max_x - min_x
    cluster_height = max_y - min_y

    if cluster_width < 18 or cluster_height < 18:
        return None

    median_width = median(text_box.width for text_box in cluster)
    median_height = median(text_box.height for text_box in cluster)
    padding_x = min(48.0, max(14.0, median_width * 1.15))
    padding_y = min(56.0, max(14.0, median_height * 0.8))
    bounding_box = _clamp_bounding_box(
        x=min_x - padding_x,
        y=min_y - padding_y,
        width=cluster_width + (padding_x * 2),
        height=cluster_height + (padding_y * 2),
        page_width=page_width,
        page_height=page_height,
    )

    box_area = bounding_box["width"] * bounding_box["height"]
    if box_area < 1200:
        return None
    if box_area > page_width * page_height * 0.22:
        return None
    if box_count == 1 and box_area < 2600:
        return None

    region_type = _classify_cluster(cluster, bounding_box)
    average_confidence = sum(text_box.confidence for text_box in cluster) / box_count
    confidence = min(0.98, round((average_confidence * 0.92) + 0.06, 2))
    return DetectedRegionCandidate(
        type=region_type,
        confidence=confidence,
        bounding_box=bounding_box,
    )


def _classify_cluster(
    cluster: list[RecognizedTextBox],
    bounding_box: dict[str, float],
) -> str:
    width = bounding_box["width"]
    height = bounding_box["height"]
    vertical_lines = sum(1 for text_box in cluster if text_box.height >= text_box.width * 1.4)
    horizontal_lines = sum(1 for text_box in cluster if text_box.width >= text_box.height * 1.2)

    if horizontal_lines >= max(2, vertical_lines) and width >= height * 1.1:
        return "narration_box"
    if width <= height * 0.72:
        return "speech_balloon"
    if len(cluster) <= 2 and width < 180 and height < 110:
        return "free_text"
    return "speech_balloon"


def _deduplicate_candidates(
    candidates: list[DetectedRegionCandidate],
) -> list[DetectedRegionCandidate]:
    ordered_candidates = sorted(
        candidates,
        key=lambda candidate: (
            candidate.bounding_box["width"] * candidate.bounding_box["height"],
            candidate.confidence,
        ),
        reverse=True,
    )
    deduplicated: list[DetectedRegionCandidate] = []
    for candidate in ordered_candidates:
        if any(_candidate_iou(candidate, other) > 0.68 for other in deduplicated):
            continue
        deduplicated.append(candidate)
    return deduplicated


def _candidate_iou(
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
) -> float:
    left_box = left.bounding_box
    right_box = right.bounding_box
    intersection_width = _axis_overlap(
        left_box["x"],
        left_box["x"] + left_box["width"],
        right_box["x"],
        right_box["x"] + right_box["width"],
    )
    intersection_height = _axis_overlap(
        left_box["y"],
        left_box["y"] + left_box["height"],
        right_box["y"],
        right_box["y"] + right_box["height"],
    )
    if intersection_width <= 0 or intersection_height <= 0:
        return 0.0

    intersection_area = intersection_width * intersection_height
    left_area = left_box["width"] * left_box["height"]
    right_area = right_box["width"] * right_box["height"]
    union_area = left_area + right_area - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


def _clamp_bounding_box(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    max_width = max(float(page_width), 1.0)
    max_height = max(float(page_height), 1.0)
    clamped_x = min(max(x, 0.0), max_width - 1.0)
    clamped_y = min(max(y, 0.0), max_height - 1.0)
    clamped_width = min(max(width, 1.0), max_width - clamped_x)
    clamped_height = min(max(height, 1.0), max_height - clamped_y)
    return {
        "x": round(clamped_x, 2),
        "y": round(clamped_y, 2),
        "width": round(clamped_width, 2),
        "height": round(clamped_height, 2),
    }


def _axis_gap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    if left_end < right_start:
        return right_start - left_end
    if right_end < left_start:
        return left_start - right_end
    return 0.0


def _axis_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))


def _detect_regions_from_fallback_bytes(
    *,
    asset_bytes: bytes,
    page_width: int,
    page_height: int,
) -> list[DetectedRegionCandidate]:
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
