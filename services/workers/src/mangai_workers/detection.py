from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING

import cv2
import numpy as np

from mangai_workers.comic_text_detector import (
    ComicTextBlock,
    extract_comic_text_detector_blocks,
)
from mangai_workers.ocr import RecognizedLine, extract_paddle_recognized_lines
from mangai_workers.runner import WorkerExecutionError


if TYPE_CHECKING:
    from mangai_workers.config import WorkerSettings


@dataclass(frozen=True)
class DetectedRegionCandidate:
    type: str
    confidence: float
    bounding_box: dict[str, float]
    text_area: dict[str, float] | None = None
    context_area: dict[str, float] | None = None
    cleanup_strategy: str | None = None
    cleanup_confidence: float | None = None

    def __post_init__(self) -> None:
        if self.text_area is None:
            object.__setattr__(self, "text_area", dict(self.bounding_box))
        if self.context_area is None:
            object.__setattr__(self, "context_area", dict(self.bounding_box))


@dataclass(frozen=True)
class RecognizedTextBox:
    text: str
    confidence: float
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class _ComicTextContainerFit:
    block: ComicTextBlock
    bounding_box: dict[str, float]
    seed_point: tuple[int, int]
    fitted_from_container: bool


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

    grayscale_image = _decode_grayscale_image(asset_bytes)

    if settings is not None:
        if settings.detection_provider == "comic_text_detector":
            try:
                detected_blocks = extract_comic_text_detector_blocks(
                    asset_path=asset_path,
                    settings=settings,
                )
                candidates = build_detected_regions_from_comic_text_blocks(
                    text_blocks=detected_blocks,
                    page_width=page_width,
                    page_height=page_height,
                    grayscale_image=grayscale_image,
                )
                if len(candidates) > 0:
                    return _annotate_cleanup_candidates(asset_path=asset_path, candidates=candidates)
            except Exception:  # noqa: BLE001 - detection should degrade gracefully
                pass

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
                return _annotate_cleanup_candidates(asset_path=asset_path, candidates=candidates)
        except Exception:  # noqa: BLE001 - region detection must degrade gracefully to fallback
            pass

    return _annotate_cleanup_candidates(
        asset_path=asset_path,
        candidates=_detect_regions_from_fallback_bytes(
            asset_bytes=asset_bytes,
            page_width=page_width,
            page_height=page_height,
        ),
    )


def build_detected_regions_from_comic_text_blocks(
    *,
    text_blocks: list[ComicTextBlock],
    page_width: int,
    page_height: int,
    grayscale_image: np.ndarray | None = None,
) -> list[DetectedRegionCandidate]:
    if grayscale_image is None:
        fits = [
            _build_simple_comic_text_fit(
                block=block,
                page_width=page_width,
                page_height=page_height,
            )
            for block in text_blocks
            if block.width >= 10 and block.height >= 10
        ]
    else:
        fits = _fit_comic_text_blocks_to_containers(
            text_blocks=text_blocks,
            grayscale_image=grayscale_image,
            page_width=page_width,
            page_height=page_height,
        )

    candidates: list[DetectedRegionCandidate] = []
    for fit in fits:
        text_area = _build_text_area_from_comic_text_block(
            block=fit.block,
            page_width=page_width,
            page_height=page_height,
        )
        if grayscale_image is not None:
            text_area = _refine_text_area_within_context_crop(
                block=fit.block,
                fallback_text_area=text_area,
                context_area=fit.bounding_box,
                grayscale_image=grayscale_image,
                page_width=page_width,
                page_height=page_height,
            )
            text_area = _tighten_text_area_to_local_dark_content(
                text_area=text_area,
                grayscale_image=grayscale_image,
                page_width=page_width,
                page_height=page_height,
                vertical=fit.block.vertical,
            )
        region_type = _classify_comic_text_block(
            block=fit.block,
            bounding_box=fit.bounding_box,
            fitted_from_container=fit.fitted_from_container,
            page_width=page_width,
            page_height=page_height,
        )
        confidence = 0.95 if fit.fitted_from_container and fit.block.language != "unknown" else 0.9
        if fit.block.language == "unknown":
            confidence -= 0.08
        candidates.append(
            DetectedRegionCandidate(
                type=region_type,
                confidence=confidence,
                bounding_box=text_area,
                text_area=text_area,
                context_area=fit.bounding_box,
            )
        )

    deduplicated = _deduplicate_candidates(candidates)
    deduplicated = _refine_candidate_context_areas(
        deduplicated,
        page_width=page_width,
        page_height=page_height,
    )
    return sorted(
        deduplicated,
        key=lambda candidate: (
            candidate.bounding_box["y"],
            candidate.bounding_box["x"],
            candidate.type,
        ),
    )


def _fit_comic_text_blocks_to_containers(
    *,
    text_blocks: list[ComicTextBlock],
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
) -> list[_ComicTextContainerFit]:
    initial_fits: list[_ComicTextContainerFit] = []
    for block in text_blocks:
        if block.width < 10 or block.height < 10:
            continue
        initial_fits.append(
            _fit_single_comic_text_block_to_container(
                block=block,
                grayscale_image=grayscale_image,
                page_width=page_width,
                page_height=page_height,
            )
        )

    grouped_fits = _group_overlapping_container_fits(initial_fits)
    resolved_fits: list[_ComicTextContainerFit] = []
    for group in grouped_fits:
        resolved_fits.extend(
            _resolve_container_fit_group(
                group=group,
                grayscale_image=grayscale_image,
                page_width=page_width,
                page_height=page_height,
            )
        )

    return sorted(
        resolved_fits,
        key=lambda fit: (
            fit.bounding_box["y"],
            fit.bounding_box["x"],
            fit.block.language,
        ),
    )


def _fit_single_comic_text_block_to_container(
    *,
    block: ComicTextBlock,
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
) -> _ComicTextContainerFit:
    group_fit = _resolve_blocks_within_container_crop(
        blocks=[block],
        fallback_fits=[
            _build_simple_comic_text_fit(
                block=block,
                page_width=page_width,
                page_height=page_height,
            )
        ],
        grayscale_image=grayscale_image,
        page_width=page_width,
        page_height=page_height,
    )
    return group_fit[0]


def _resolve_container_fit_group(
    *,
    group: list[_ComicTextContainerFit],
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
) -> list[_ComicTextContainerFit]:
    if len(group) <= 1:
        return group

    return _resolve_blocks_within_container_crop(
        blocks=[fit.block for fit in group],
        fallback_fits=group,
        grayscale_image=grayscale_image,
        page_width=page_width,
        page_height=page_height,
    )


def _resolve_blocks_within_container_crop(
    *,
    blocks: list[ComicTextBlock],
    fallback_fits: list[_ComicTextContainerFit],
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
) -> list[_ComicTextContainerFit]:
    crop_bounds = _compute_container_crop_bounds(
        blocks=blocks,
        page_width=page_width,
        page_height=page_height,
    )
    crop_x1, crop_y1, crop_x2, crop_y2 = crop_bounds
    crop = grayscale_image[crop_y1:crop_y2, crop_x1:crop_x2]
    if crop.size == 0:
        return fallback_fits

    free_mask = _build_container_free_mask(crop)
    if np.count_nonzero(free_mask) == 0:
        return fallback_fits

    distance_map = cv2.distanceTransform(free_mask.astype(np.uint8), cv2.DIST_L2, 5)
    _label_count, labels, _stats, _centroids = cv2.connectedComponentsWithStats(
        free_mask.astype(np.uint8),
        connectivity=8,
    )

    seed_lookup: dict[int, tuple[int, int]] = {}
    support_masks: dict[int, np.ndarray] = {}
    for index, block in enumerate(blocks):
        local_seed = _find_best_seed_point(
            distance_map=distance_map,
            free_mask=free_mask,
            block=block,
            crop_origin=(crop_x1, crop_y1),
        )
        seed_lookup[index] = local_seed
        support_masks[index] = _build_support_mask_for_block(
            labels=labels,
            block=block,
            crop_origin=(crop_x1, crop_y1),
            seed_point=local_seed,
        )

    grouped_indexes = _group_block_support_masks(support_masks)

    resolved_lookup: dict[int, _ComicTextContainerFit] = {}
    for member_indexes in grouped_indexes:
        component_masks = [support_masks[member_index] for member_index in member_indexes]
        component_mask = np.logical_or.reduce(component_masks)
        if np.count_nonzero(component_mask) == 0:
            for member_index in member_indexes:
                resolved_lookup[member_index] = fallback_fits[member_index]
            continue

        if len(member_indexes) == 1:
            member_index = member_indexes[0]
            bounding_box = _build_container_bounding_box_for_block(
                component_mask=component_mask,
                block=blocks[member_index],
                crop_origin=(crop_x1, crop_y1),
                page_width=page_width,
                page_height=page_height,
            )
            resolved_lookup[member_index] = _ComicTextContainerFit(
                block=blocks[member_index],
                bounding_box=bounding_box,
                seed_point=(
                    crop_x1 + seed_lookup[member_index][0],
                    crop_y1 + seed_lookup[member_index][1],
                ),
                fitted_from_container=True,
            )
            continue

        split_fits = _split_shared_container_component(
            component_mask=component_mask,
            member_indexes=member_indexes,
            blocks=blocks,
            seed_lookup=seed_lookup,
            crop_origin=(crop_x1, crop_y1),
            page_width=page_width,
            page_height=page_height,
        )
        if split_fits is None:
            for member_index in member_indexes:
                resolved_lookup[member_index] = fallback_fits[member_index]
            continue

        for member_index, fit in split_fits.items():
            resolved_lookup[member_index] = fit

    return [resolved_lookup.get(index, fallback_fits[index]) for index in range(len(blocks))]


def _group_overlapping_container_fits(
    fits: list[_ComicTextContainerFit],
) -> list[list[_ComicTextContainerFit]]:
    if len(fits) <= 1:
        return [[fit] for fit in fits]

    parents = list(range(len(fits)))

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

    for left_index in range(len(fits)):
        for right_index in range(left_index + 1, len(fits)):
            if _should_group_container_fits(fits[left_index], fits[right_index]):
                union(left_index, right_index)

    grouped: dict[int, list[_ComicTextContainerFit]] = {}
    for index, fit in enumerate(fits):
        grouped.setdefault(find(index), []).append(fit)

    return sorted(
        grouped.values(),
        key=lambda group: (
            min(fit.bounding_box["y"] for fit in group),
            min(fit.bounding_box["x"] for fit in group),
        ),
    )


def _should_group_container_fits(
    left: _ComicTextContainerFit,
    right: _ComicTextContainerFit,
) -> bool:
    left_box = left.bounding_box
    right_box = right.bounding_box
    iou = _bounding_box_iou(left_box, right_box)
    if iou >= 0.18:
        return True

    horizontal_gap = _axis_gap(
        left_box["x"],
        left_box["x"] + left_box["width"],
        right_box["x"],
        right_box["x"] + right_box["width"],
    )
    vertical_gap = _axis_gap(
        left_box["y"],
        left_box["y"] + left_box["height"],
        right_box["y"],
        right_box["y"] + right_box["height"],
    )
    horizontal_overlap = _axis_overlap(
        left_box["x"],
        left_box["x"] + left_box["width"],
        right_box["x"],
        right_box["x"] + right_box["width"],
    )
    vertical_overlap = _axis_overlap(
        left_box["y"],
        left_box["y"] + left_box["height"],
        right_box["y"],
        right_box["y"] + right_box["height"],
    )

    min_width = max(min(left_box["width"], right_box["width"]), 1.0)
    min_height = max(min(left_box["height"], right_box["height"]), 1.0)
    if horizontal_gap <= max(18.0, min_width * 0.18) and vertical_overlap >= min_height * 0.42:
        return True
    if vertical_gap <= max(18.0, min_height * 0.18) and horizontal_overlap >= min_width * 0.42:
        return True
    return False


def _build_support_mask_for_block(
    *,
    labels: np.ndarray,
    block: ComicTextBlock,
    crop_origin: tuple[int, int],
    seed_point: tuple[int, int],
) -> np.ndarray:
    crop_x, crop_y = crop_origin
    halo_x = max(18, int(round(max(block.width * 2.2, block.height * 0.55))))
    halo_y = max(12, int(round(max(block.height * 0.24, block.width * 1.4))))
    x1 = max(int(np.floor(block.x - crop_x - halo_x)), 0)
    y1 = max(int(np.floor(block.y - crop_y - halo_y)), 0)
    x2 = min(int(np.ceil(block.x + block.width - crop_x + halo_x)), labels.shape[1])
    y2 = min(int(np.ceil(block.y + block.height - crop_y + halo_y)), labels.shape[0])

    label_window = labels[y1:y2, x1:x2]
    component_labels = {int(value) for value in np.unique(label_window) if int(value) > 0}
    seed_label = int(labels[seed_point[1], seed_point[0]])
    if seed_label > 0:
        component_labels.add(seed_label)

    if len(component_labels) == 0:
        return np.zeros_like(labels, dtype=bool)

    boundary_labels = {
        int(value)
        for value in np.concatenate(
            (
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            )
        )
        if int(value) > 0
    }
    interior_labels = component_labels.difference(boundary_labels)
    selected_labels = interior_labels if len(interior_labels) > 0 else component_labels
    return np.isin(labels, list(selected_labels))


def _group_block_support_masks(
    support_masks: dict[int, np.ndarray],
) -> list[list[int]]:
    indexes = sorted(support_masks.keys())
    if len(indexes) <= 1:
        return [[index] for index in indexes]

    parents = list(range(len(indexes)))

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

    for left_position in range(len(indexes)):
        for right_position in range(left_position + 1, len(indexes)):
            left_mask = support_masks[indexes[left_position]]
            right_mask = support_masks[indexes[right_position]]
            if np.any(np.logical_and(left_mask, right_mask)):
                union(left_position, right_position)

    grouped: dict[int, list[int]] = {}
    for position, index in enumerate(indexes):
        grouped.setdefault(find(position), []).append(index)

    return list(grouped.values())


def _split_shared_container_component(
    *,
    component_mask: np.ndarray,
    member_indexes: list[int],
    blocks: list[ComicTextBlock],
    seed_lookup: dict[int, tuple[int, int]],
    crop_origin: tuple[int, int],
    page_width: int,
    page_height: int,
) -> dict[int, _ComicTextContainerFit] | None:
    y_values, x_values = np.nonzero(component_mask)
    if len(x_values) == 0:
        return None

    seed_points = np.array([seed_lookup[member_index] for member_index in member_indexes], dtype=np.int32)
    pixel_points = np.column_stack((x_values, y_values)).astype(np.float32)
    distances = np.sum(
        (pixel_points[:, None, :] - seed_points[None, :, :].astype(np.float32)) ** 2,
        axis=2,
    )
    assignments = np.argmin(distances, axis=1)

    resolved: dict[int, _ComicTextContainerFit] = {}
    for assignment_index, member_index in enumerate(member_indexes):
        assigned_mask = np.zeros_like(component_mask, dtype=np.uint8)
        assigned_pixels = assignments == assignment_index
        assigned_mask[y_values[assigned_pixels], x_values[assigned_pixels]] = 1
        if np.count_nonzero(assigned_mask) == 0:
            return None

        local_seed = seed_lookup[member_index]
        seed_x = min(max(local_seed[0], 0), assigned_mask.shape[1] - 1)
        seed_y = min(max(local_seed[1], 0), assigned_mask.shape[0] - 1)
        label_count, labels, _stats, _centroids = cv2.connectedComponentsWithStats(assigned_mask, connectivity=8)
        if label_count <= 1:
            return None
        seed_label = int(labels[seed_y, seed_x])
        if seed_label <= 0:
            return None

        split_mask = labels == seed_label
        bounding_box = _build_container_bounding_box_for_block(
            component_mask=split_mask,
            block=blocks[member_index],
            crop_origin=crop_origin,
            page_width=page_width,
            page_height=page_height,
        )
        resolved[member_index] = _ComicTextContainerFit(
            block=blocks[member_index],
            bounding_box=bounding_box,
            seed_point=(crop_origin[0] + seed_x, crop_origin[1] + seed_y),
            fitted_from_container=True,
        )
    return resolved


def _compute_container_crop_bounds(
    *,
    blocks: list[ComicTextBlock],
    page_width: int,
    page_height: int,
) -> tuple[int, int, int, int]:
    min_x = min(block.x for block in blocks)
    min_y = min(block.y for block in blocks)
    max_x = max(block.x + block.width for block in blocks)
    max_y = max(block.y + block.height for block in blocks)
    max_block_width = max(block.width for block in blocks)
    max_block_height = max(block.height for block in blocks)
    group_scale = 1.0 + min(0.45, max(0, len(blocks) - 1) * 0.12)

    margin_x = max(48.0, max_block_width * 1.05, max_block_height * 0.7) * group_scale
    margin_y = max(38.0, max_block_height * 0.5, max_block_width * 0.9) * group_scale

    x1 = max(int(np.floor(min_x - margin_x)), 0)
    y1 = max(int(np.floor(min_y - margin_y)), 0)
    x2 = min(int(np.ceil(max_x + margin_x)), page_width)
    y2 = min(int(np.ceil(max_y + margin_y)), page_height)
    return x1, y1, x2, y2


def _build_container_free_mask(grayscale_crop: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(grayscale_crop, (0, 0), sigmaX=1.8, sigmaY=1.8)
    bright_smooth_mask = _build_bright_smooth_container_mask(blurred)
    barrier_mask = _build_container_barrier_mask(blurred)
    free_mask = np.logical_and(bright_smooth_mask, np.logical_not(barrier_mask))
    if np.count_nonzero(free_mask) >= max(42, int(grayscale_crop.size * 0.002)):
        return free_mask
    return np.logical_not(barrier_mask)


def _build_container_barrier_mask(blurred_crop: np.ndarray) -> np.ndarray:
    dark_threshold = _pick_container_dark_threshold(blurred_crop)
    barrier_mask = blurred_crop <= dark_threshold
    edge_mask = cv2.Canny(
        blurred_crop,
        threshold1=max(30, int(dark_threshold * 0.5)),
        threshold2=max(60, int(dark_threshold * 1.1)),
    ) > 0
    barrier_mask = np.logical_or(barrier_mask, edge_mask)
    barrier_mask = cv2.dilate(
        barrier_mask.astype(np.uint8),
        np.ones((3, 3), dtype=np.uint8),
        iterations=1,
    ).astype(bool)
    barrier_mask = cv2.morphologyEx(
        barrier_mask.astype(np.uint8),
        cv2.MORPH_CLOSE,
        np.ones((5, 5), dtype=np.uint8),
        iterations=1,
    ).astype(bool)
    barrier_mask[0, :] = True
    barrier_mask[-1, :] = True
    barrier_mask[:, 0] = True
    barrier_mask[:, -1] = True
    return barrier_mask


def _build_bright_smooth_container_mask(blurred_crop: np.ndarray) -> np.ndarray:
    float_crop = blurred_crop.astype(np.float32)
    local_mean = cv2.GaussianBlur(float_crop, (0, 0), sigmaX=5.2, sigmaY=5.2)
    squared_mean = cv2.GaussianBlur(float_crop * float_crop, (0, 0), sigmaX=5.2, sigmaY=5.2)
    local_variance = np.maximum(squared_mean - (local_mean * local_mean), 0.0)
    local_std = np.sqrt(local_variance)

    bright_threshold = _pick_container_bright_threshold(blurred_crop)
    smooth_threshold = _pick_container_smooth_threshold(local_std)
    candidate_mask = np.logical_and(blurred_crop >= bright_threshold, local_std <= smooth_threshold)
    candidate_mask = cv2.morphologyEx(
        candidate_mask.astype(np.uint8),
        cv2.MORPH_CLOSE,
        np.ones((5, 5), dtype=np.uint8),
        iterations=1,
    ).astype(bool)
    candidate_mask = cv2.morphologyEx(
        candidate_mask.astype(np.uint8),
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
        iterations=1,
    ).astype(bool)
    return _drop_small_connected_components(
        candidate_mask,
        minimum_pixels=max(48, int(candidate_mask.size * 0.0018)),
    )


def _pick_container_dark_threshold(grayscale_crop: np.ndarray) -> int:
    p10 = float(np.percentile(grayscale_crop, 10))
    p25 = float(np.percentile(grayscale_crop, 25))
    threshold = int(round((p10 * 0.38) + (p25 * 0.62) + 16.0))
    return max(135, min(185, threshold))


def _pick_container_bright_threshold(grayscale_crop: np.ndarray) -> int:
    otsu_threshold, _ = cv2.threshold(
        grayscale_crop,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    p70 = float(np.percentile(grayscale_crop, 70))
    p88 = float(np.percentile(grayscale_crop, 88))
    threshold = int(round(max(otsu_threshold + 6.0, (p70 * 0.22) + (p88 * 0.78))))
    return max(184, min(242, threshold))


def _pick_container_smooth_threshold(local_std: np.ndarray) -> float:
    p35 = float(np.percentile(local_std, 35))
    p55 = float(np.percentile(local_std, 55))
    return max(8.5, min(24.0, (p35 * 0.58) + (p55 * 0.42) + 2.5))


def _drop_small_connected_components(mask: np.ndarray, *, minimum_pixels: int) -> np.ndarray:
    if np.count_nonzero(mask) == 0:
        return mask

    label_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8),
        connectivity=8,
    )
    if label_count <= 1:
        return mask

    filtered_mask = np.zeros_like(mask, dtype=bool)
    for label_index in range(1, label_count):
        area = int(stats[label_index, cv2.CC_STAT_AREA])
        if area < minimum_pixels:
            continue
        filtered_mask = np.logical_or(filtered_mask, labels == label_index)
    return filtered_mask


def _find_best_seed_point(
    *,
    distance_map: np.ndarray,
    free_mask: np.ndarray,
    block: ComicTextBlock,
    crop_origin: tuple[int, int],
) -> tuple[int, int]:
    crop_x, crop_y = crop_origin
    margin_x = max(8, int(round(block.width * 0.18)))
    margin_y = max(8, int(round(block.height * 0.12)))
    x1 = max(int(np.floor(block.x - crop_x - margin_x)), 0)
    y1 = max(int(np.floor(block.y - crop_y - margin_y)), 0)
    x2 = min(int(np.ceil(block.x + block.width - crop_x + margin_x)), free_mask.shape[1])
    y2 = min(int(np.ceil(block.y + block.height - crop_y + margin_y)), free_mask.shape[0])

    if x2 > x1 and y2 > y1:
        region_distance = distance_map[y1:y2, x1:x2]
        if region_distance.size > 0 and float(np.max(region_distance)) > 0:
            local_y, local_x = np.unravel_index(np.argmax(region_distance), region_distance.shape)
            return x1 + int(local_x), y1 + int(local_y)

    free_y, free_x = np.nonzero(free_mask)
    if len(free_x) == 0:
        return min(max(x1, 0), free_mask.shape[1] - 1), min(max(y1, 0), free_mask.shape[0] - 1)

    target_x = (block.x + (block.width / 2.0)) - crop_x
    target_y = (block.y + (block.height / 2.0)) - crop_y
    distances = ((free_x - target_x) ** 2) + ((free_y - target_y) ** 2)
    best_index = int(np.argmin(distances))
    return int(free_x[best_index]), int(free_y[best_index])


def _build_container_bounding_box_for_block(
    *,
    component_mask: np.ndarray,
    block: ComicTextBlock,
    crop_origin: tuple[int, int],
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    component_box = _mask_to_bounding_box(
        mask=component_mask,
        crop_origin=crop_origin,
        page_width=page_width,
        page_height=page_height,
    )
    if _mask_touches_crop_boundary(component_mask) or _looks_like_leaked_container(
        component_box=component_box,
        block=block,
    ):
        return _build_leak_resistant_comic_text_bounding_box(
            block=block,
            page_width=page_width,
            page_height=page_height,
        )

    text_guard_box = _clamp_bounding_box(
        x=block.x - 6.0,
        y=block.y - 6.0,
        width=block.width + 12.0,
        height=block.height + 12.0,
        page_width=page_width,
        page_height=page_height,
    )
    return _merge_bounding_boxes(component_box, text_guard_box, page_width=page_width, page_height=page_height)


def _looks_like_leaked_container(
    *,
    component_box: dict[str, float],
    block: ComicTextBlock,
) -> bool:
    max_reasonable_width = (
        max(block.width * 4.8, block.height * 1.36)
        if block.vertical
        else max(block.width * 1.28, block.height * 4.2)
    )
    max_reasonable_height = (
        max(block.height * 2.2, block.width * 5.6)
        if block.vertical
        else max(block.height * 3.2, block.width * 0.28)
    )
    return (
        component_box["width"] > max_reasonable_width
        or component_box["height"] > max_reasonable_height
    )


def _mask_touches_crop_boundary(
    mask: np.ndarray,
    *,
    margin: int = 1,
    minimum_boundary_pixels: int = 8,
) -> bool:
    if mask.size == 0:
        return False

    margin = max(1, margin)
    boundary_pixel_count = int(
        np.count_nonzero(mask[:margin, :])
        + np.count_nonzero(mask[-margin:, :])
        + np.count_nonzero(mask[:, :margin])
        + np.count_nonzero(mask[:, -margin:])
    )
    return boundary_pixel_count >= minimum_boundary_pixels


def _build_leak_resistant_comic_text_bounding_box(
    *,
    block: ComicTextBlock,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    if block.vertical:
        padding_x = min(68.0, max(28.0, block.width * 2.1, block.height * 0.42))
        padding_y = min(42.0, max(16.0, block.height * 0.24, block.width * 1.15))
    else:
        padding_x = min(48.0, max(14.0, block.width * 0.24, block.height * 0.5))
        padding_y = min(40.0, max(14.0, block.height * 0.44, block.width * 0.18))

    return _clamp_bounding_box(
        x=block.x - padding_x,
        y=block.y - padding_y,
        width=block.width + (padding_x * 2.0),
        height=block.height + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )


def _mask_to_bounding_box(
    *,
    mask: np.ndarray,
    crop_origin: tuple[int, int],
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    y_values, x_values = np.nonzero(mask)
    if len(x_values) == 0:
        return _clamp_bounding_box(
            x=float(crop_origin[0]),
            y=float(crop_origin[1]),
            width=1.0,
            height=1.0,
            page_width=page_width,
            page_height=page_height,
        )

    x1 = crop_origin[0] + int(np.min(x_values))
    y1 = crop_origin[1] + int(np.min(y_values))
    x2 = crop_origin[0] + int(np.max(x_values)) + 1
    y2 = crop_origin[1] + int(np.max(y_values)) + 1
    padding = 3.0
    return _clamp_bounding_box(
        x=float(x1 - padding),
        y=float(y1 - padding),
        width=float((x2 - x1) + (padding * 2)),
        height=float((y2 - y1) + (padding * 2)),
        page_width=page_width,
        page_height=page_height,
    )


def _merge_bounding_boxes(
    left: dict[str, float],
    right: dict[str, float],
    *,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    min_x = min(left["x"], right["x"])
    min_y = min(left["y"], right["y"])
    max_x = max(left["x"] + left["width"], right["x"] + right["width"])
    max_y = max(left["y"] + left["height"], right["y"] + right["height"])
    return _clamp_bounding_box(
        x=min_x,
        y=min_y,
        width=max_x - min_x,
        height=max_y - min_y,
        page_width=page_width,
        page_height=page_height,
    )


def _intersect_bounding_boxes(
    left: dict[str, float],
    right: dict[str, float],
    *,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    x1 = max(left["x"], right["x"])
    y1 = max(left["y"], right["y"])
    x2 = min(left["x"] + left["width"], right["x"] + right["width"])
    y2 = min(left["y"] + left["height"], right["y"] + right["height"])
    if x2 <= x1 or y2 <= y1:
        return right

    return _clamp_bounding_box(
        x=x1,
        y=y1,
        width=x2 - x1,
        height=y2 - y1,
        page_width=page_width,
        page_height=page_height,
    )


def _build_simple_comic_text_fit(
    *,
    block: ComicTextBlock,
    page_width: int,
    page_height: int,
) -> _ComicTextContainerFit:
    bounding_box = _build_simple_comic_text_bounding_box(
        block=block,
        page_width=page_width,
        page_height=page_height,
    )
    seed_x = int(round(block.x + (block.width / 2.0)))
    seed_y = int(round(block.y + (block.height / 2.0)))
    return _ComicTextContainerFit(
        block=block,
        bounding_box=bounding_box,
        seed_point=(seed_x, seed_y),
        fitted_from_container=False,
    )


def _build_simple_comic_text_bounding_box(
    *,
    block: ComicTextBlock,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    padding_x = min(18.0, max(6.0, block.width * 0.08))
    padding_y = min(18.0, max(6.0, block.height * 0.08))
    return _clamp_bounding_box(
        x=block.x - padding_x,
        y=block.y - padding_y,
        width=block.width + (padding_x * 2.0),
        height=block.height + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )


def _build_text_area_from_comic_text_block(
    *,
    block: ComicTextBlock,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    padding_x = min(8.0, max(2.0, block.width * 0.04))
    padding_y = min(8.0, max(2.0, block.height * 0.04))
    return _clamp_bounding_box(
        x=block.x - padding_x,
        y=block.y - padding_y,
        width=block.width + (padding_x * 2.0),
        height=block.height + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )


def _refine_text_area_within_context_crop(
    *,
    block: ComicTextBlock,
    fallback_text_area: dict[str, float],
    context_area: dict[str, float],
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    x1 = max(int(np.floor(context_area["x"])), 0)
    y1 = max(int(np.floor(context_area["y"])), 0)
    x2 = min(int(np.ceil(context_area["x"] + context_area["width"])), grayscale_image.shape[1])
    y2 = min(int(np.ceil(context_area["y"] + context_area["height"])), grayscale_image.shape[0])
    if x2 <= x1 or y2 <= y1:
        return fallback_text_area

    crop = grayscale_image[y1:y2, x1:x2]
    if crop.size == 0:
        return fallback_text_area

    blurred = cv2.GaussianBlur(crop, (3, 3), 0)
    threshold_value, thresholded = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    # Otsu can drift too bright on clean balloons; cap the text threshold to stay selective.
    effective_threshold = int(min(max(threshold_value, 72), 188))
    raw_dark_mask = (crop <= effective_threshold).astype(np.uint8) * 255
    dark_mask = (blurred <= effective_threshold).astype(np.uint8) * 255
    dark_mask = cv2.bitwise_or(dark_mask, raw_dark_mask)
    dark_mask = cv2.medianBlur(dark_mask, 3)

    kernel_size = 2 if max(block.width, block.height) < 120 else 3
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)

    anchor_box = _compute_text_refinement_anchor_box(
        block=block,
        crop_origin=(x1, y1),
        crop_shape=crop.shape,
    )
    anchor_x1 = int(np.floor(anchor_box["x"]))
    anchor_y1 = int(np.floor(anchor_box["y"]))
    anchor_x2 = int(np.ceil(anchor_box["x"] + anchor_box["width"]))
    anchor_y2 = int(np.ceil(anchor_box["y"] + anchor_box["height"]))
    anchor_mask = dark_mask[anchor_y1:anchor_y2, anchor_x1:anchor_x2]
    anchor_mask = _remove_anchor_boundary_artifacts(anchor_mask)
    sparse_anchor_mask = raw_dark_mask[anchor_y1:anchor_y2, anchor_x1:anchor_x2]
    sparse_anchor_mask = _remove_anchor_boundary_artifacts(sparse_anchor_mask)
    if anchor_mask.size == 0 or np.count_nonzero(anchor_mask) == 0:
        return fallback_text_area

    valid_columns = _dense_axis_mask(
        np.count_nonzero(anchor_mask, axis=0),
        min_pixels=max(2, int(round(anchor_mask.shape[0] * (0.045 if block.vertical else 0.085)))),
    )
    valid_rows = _dense_axis_mask(
        np.count_nonzero(anchor_mask, axis=1),
        min_pixels=max(2, int(round(anchor_mask.shape[1] * (0.03 if block.vertical else 0.07)))),
    )
    if not valid_columns.any() or not valid_rows.any():
        return fallback_text_area

    seed_x1 = max(int(np.floor(block.x - x1)) - anchor_x1, 0)
    seed_y1 = max(int(np.floor(block.y - y1)) - anchor_y1, 0)
    seed_x2 = min(int(np.ceil(block.x + block.width - x1)) - anchor_x1, anchor_mask.shape[1])
    seed_y2 = min(int(np.ceil(block.y + block.height - y1)) - anchor_y1, anchor_mask.shape[0])

    selected_column_range = _expand_dense_axis_range(
        valid_mask=valid_columns,
        seed_start=seed_x1,
        seed_end=max(seed_x2, seed_x1 + 1),
    )
    selected_row_range = _expand_dense_axis_range(
        valid_mask=valid_rows,
        seed_start=seed_y1,
        seed_end=max(seed_y2, seed_y1 + 1),
    )
    if selected_column_range is None or selected_row_range is None:
        return fallback_text_area

    selected_column_range = _extend_axis_range_with_sparse_neighbors(
        counts=np.count_nonzero(sparse_anchor_mask, axis=0),
        selected_range=selected_column_range,
        min_pixels=1,
        max_gap=8 if block.vertical else 3,
        max_extension=max(
            10 if block.vertical else 6,
            int(round(max(block.width * (1.1 if block.vertical else 0.24), block.height * 0.08))),
        ),
    )
    selected_row_range = _extend_axis_range_with_sparse_neighbors(
        counts=np.count_nonzero(sparse_anchor_mask, axis=1),
        selected_range=selected_row_range,
        min_pixels=1,
        max_gap=4 if block.vertical else 3,
        max_extension=max(8, int(round(block.height * (0.16 if block.vertical else 0.4)))),
    )

    column_start, column_end = selected_column_range
    row_start, row_end = selected_row_range
    component_bounds = _build_relevant_text_component_bounds(
        mask=sparse_anchor_mask,
        anchor_box={
            "x": float(column_start),
            "y": float(row_start),
            "width": float(max(column_end - column_start, 1)),
            "height": float(max(row_end - row_start, 1)),
        },
        block=block,
    )
    if component_bounds is not None:
        column_start = min(column_start, int(np.floor(component_bounds["x"])))
        row_start = min(row_start, int(np.floor(component_bounds["y"])))
        column_end = max(column_end, int(np.ceil(component_bounds["x"] + component_bounds["width"])))
        row_end = max(row_end, int(np.ceil(component_bounds["y"] + component_bounds["height"])))
    if column_end <= column_start or row_end <= row_start:
        return fallback_text_area

    refined_x1 = x1 + anchor_x1 + column_start
    refined_y1 = y1 + anchor_y1 + row_start
    refined_x2 = x1 + anchor_x1 + column_end
    refined_y2 = y1 + anchor_y1 + row_end

    selected_width = max(refined_x2 - refined_x1, 1)
    selected_height = max(refined_y2 - refined_y1, 1)
    if block.vertical:
        padding_x = min(12.0, max(4.0, selected_width * 0.18, selected_height * 0.04))
        padding_y = min(12.0, max(4.0, selected_height * 0.08))
    else:
        padding_x = min(12.0, max(4.0, selected_width * 0.05))
        padding_y = min(10.0, max(3.0, selected_height * 0.18, selected_width * 0.02))

    refined_box = _clamp_bounding_box(
        x=float(refined_x1) - padding_x,
        y=float(refined_y1) - padding_y,
        width=float(selected_width) + (padding_x * 2.0),
        height=float(selected_height) + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )
    center_guard_width = min(max(block.width * 0.24, 6.0), max(block.width * 0.5, 12.0))
    center_guard_height = min(max(block.height * 0.24, 8.0), max(block.height * 0.5, 18.0))
    center_guard = _clamp_bounding_box(
        x=(block.x + (block.width / 2.0)) - (center_guard_width / 2.0),
        y=(block.y + (block.height / 2.0)) - (center_guard_height / 2.0),
        width=center_guard_width,
        height=center_guard_height,
        page_width=page_width,
        page_height=page_height,
    )
    final_box = _merge_bounding_boxes(
        refined_box,
        center_guard,
        page_width=page_width,
        page_height=page_height,
    )
    refinement_guard = _build_text_refinement_guard_box(
        block=block,
        fallback_text_area=fallback_text_area,
        page_width=page_width,
        page_height=page_height,
    )
    final_box = _intersect_bounding_boxes(
        final_box,
        refinement_guard,
        page_width=page_width,
        page_height=page_height,
    )
    if (
        final_box["width"] >= fallback_text_area["width"]
        and final_box["height"] >= fallback_text_area["height"]
    ):
        return fallback_text_area
    return final_box


def _tighten_text_area_to_local_dark_content(
    *,
    text_area: dict[str, float],
    grayscale_image: np.ndarray,
    page_width: int,
    page_height: int,
    vertical: bool,
) -> dict[str, float]:
    x1 = max(int(np.floor(text_area["x"])), 0)
    y1 = max(int(np.floor(text_area["y"])), 0)
    x2 = min(int(np.ceil(text_area["x"] + text_area["width"])), grayscale_image.shape[1])
    y2 = min(int(np.ceil(text_area["y"] + text_area["height"])), grayscale_image.shape[0])
    if x2 <= x1 or y2 <= y1:
        return text_area

    crop = grayscale_image[y1:y2, x1:x2]
    if crop.size == 0:
        return text_area

    blurred = cv2.GaussianBlur(crop, (3, 3), 0)
    threshold_value, _ = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    effective_threshold = int(min(max(threshold_value, 72), 188))
    raw_dark_mask = (crop <= effective_threshold).astype(np.uint8) * 255
    dark_mask = (blurred <= effective_threshold).astype(np.uint8) * 255
    dark_mask = cv2.bitwise_or(dark_mask, raw_dark_mask)
    dark_mask = _remove_anchor_boundary_artifacts(dark_mask)
    if np.count_nonzero(dark_mask) == 0:
        return text_area

    y_values, x_values = np.nonzero(dark_mask)
    if len(x_values) == 0:
        return text_area

    dark_x1 = int(np.min(x_values))
    dark_y1 = int(np.min(y_values))
    dark_x2 = int(np.max(x_values)) + 1
    dark_y2 = int(np.max(y_values)) + 1

    dark_width = max(dark_x2 - dark_x1, 1)
    dark_height = max(dark_y2 - dark_y1, 1)
    if vertical:
        padding_x = min(7.0, max(3.0, dark_width * 0.08))
        padding_y = min(10.0, max(4.0, dark_height * 0.05))
    else:
        padding_x = min(10.0, max(4.0, dark_width * 0.03))
        padding_y = min(6.0, max(2.0, dark_height * 0.1))

    tightened = _clamp_bounding_box(
        x=x1 + dark_x1 - padding_x,
        y=y1 + dark_y1 - padding_y,
        width=dark_width + (padding_x * 2.0),
        height=dark_height + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )
    width_gain = text_area["width"] - tightened["width"]
    height_gain = text_area["height"] - tightened["height"]
    if width_gain < 4.0 and height_gain < 4.0:
        return text_area
    return tightened


def _dense_axis_mask(counts: np.ndarray, *, min_pixels: int) -> np.ndarray:
    valid_mask = counts >= max(min_pixels, 1)
    if valid_mask.size <= 2:
        return valid_mask

    # Fill tiny gaps so punctuation/ruby doesn't split one text column into multiple segments.
    filled = valid_mask.copy()
    for index in range(1, len(valid_mask) - 1):
        if not valid_mask[index] and valid_mask[index - 1] and valid_mask[index + 1]:
            filled[index] = True
    return filled


def _extend_axis_range_with_sparse_neighbors(
    *,
    counts: np.ndarray,
    selected_range: tuple[int, int],
    min_pixels: int,
    max_gap: int,
    max_extension: int,
) -> tuple[int, int]:
    start, end = selected_range
    if counts.size == 0 or max_extension <= 0:
        return selected_range

    start = max(min(start, len(counts) - 1), 0)
    end = max(min(end, len(counts)), start + 1)

    gap = 0
    extension = 0
    cursor = start - 1
    while cursor >= 0 and extension < max_extension:
        if counts[cursor] >= min_pixels:
            start = cursor
            gap = 0
        else:
            gap += 1
            if gap > max_gap:
                break
        cursor -= 1
        extension += 1

    gap = 0
    extension = 0
    cursor = end
    while cursor < len(counts) and extension < max_extension:
        if counts[cursor] >= min_pixels:
            end = cursor + 1
            gap = 0
        else:
            gap += 1
            if gap > max_gap:
                break
        cursor += 1
        extension += 1

    return start, end


def _remove_anchor_boundary_artifacts(mask: np.ndarray) -> np.ndarray:
    if mask.size == 0 or np.count_nonzero(mask) == 0:
        return mask

    component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if component_count <= 1:
        return mask

    cleaned = np.zeros_like(mask, dtype=np.uint8)
    mask_height, mask_width = mask.shape
    for component_index in range(1, component_count):
        area = int(stats[component_index, cv2.CC_STAT_AREA])
        component_x = int(stats[component_index, cv2.CC_STAT_LEFT])
        component_y = int(stats[component_index, cv2.CC_STAT_TOP])
        component_w = int(stats[component_index, cv2.CC_STAT_WIDTH])
        component_h = int(stats[component_index, cv2.CC_STAT_HEIGHT])
        touches_boundary = (
            component_x == 0
            or component_y == 0
            or (component_x + component_w) >= mask_width
            or (component_y + component_h) >= mask_height
        )
        if area < 3:
            continue
        if area < 8 and not touches_boundary:
            cleaned[labels == component_index] = 255
            continue

        bbox_area = max(component_w * component_h, 1)
        fill_ratio = area / bbox_area
        long_span = (
            component_w >= max(mask_width * 0.32, component_h * 4.8)
            or component_h >= max(mask_height * 0.32, component_w * 4.8)
        )
        large_sparse = fill_ratio < 0.22 and (
            component_w >= mask_width * 0.24 or component_h >= mask_height * 0.24
        )
        if touches_boundary and (long_span or large_sparse):
            continue

        cleaned[labels == component_index] = 255

    return cleaned if np.count_nonzero(cleaned) > 0 else mask


def _build_text_refinement_guard_box(
    *,
    block: ComicTextBlock,
    fallback_text_area: dict[str, float],
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    if block.vertical:
        padding_x = min(20.0, max(6.0, block.width * 0.42, block.height * 0.045))
        padding_y = min(18.0, max(5.0, block.height * 0.08, block.width * 0.28))
    else:
        padding_x = min(18.0, max(5.0, block.width * 0.08, block.height * 0.24))
        padding_y = min(16.0, max(5.0, block.height * 0.14, block.width * 0.035))

    return _clamp_bounding_box(
        x=fallback_text_area["x"] - padding_x,
        y=fallback_text_area["y"] - padding_y,
        width=fallback_text_area["width"] + (padding_x * 2.0),
        height=fallback_text_area["height"] + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )


def _expand_dense_axis_range(
    *,
    valid_mask: np.ndarray,
    seed_start: int,
    seed_end: int,
    allowed_gap: int = 2,
) -> tuple[int, int] | None:
    if valid_mask.size == 0:
        return None

    seed_start = max(min(seed_start, len(valid_mask) - 1), 0)
    seed_end = max(min(seed_end, len(valid_mask)), seed_start + 1)
    active_indexes = np.flatnonzero(valid_mask)
    if len(active_indexes) == 0:
        return None

    seed_slice = active_indexes[(active_indexes >= seed_start) & (active_indexes < seed_end)]
    if len(seed_slice) == 0:
        seed_center = int(round((seed_start + seed_end - 1) / 2.0))
        seed_index = int(active_indexes[np.argmin(np.abs(active_indexes - seed_center))])
        left = seed_index
        right = seed_index
    else:
        left = int(seed_slice[0])
        right = int(seed_slice[-1])

    gap = 0
    cursor = left - 1
    while cursor >= 0:
        if valid_mask[cursor]:
            left = cursor
            gap = 0
        else:
            gap += 1
            if gap > allowed_gap:
                break
        cursor -= 1

    gap = 0
    cursor = right + 1
    while cursor < len(valid_mask):
        if valid_mask[cursor]:
            right = cursor
            gap = 0
        else:
            gap += 1
            if gap > allowed_gap:
                break
        cursor += 1

    return left, right + 1


def _compute_text_refinement_anchor_box(
    *,
    block: ComicTextBlock,
    crop_origin: tuple[int, int],
    crop_shape: tuple[int, int],
) -> dict[str, float]:
    crop_x, crop_y = crop_origin
    crop_height, crop_width = crop_shape
    if block.vertical:
        margin_x = max(10.0, block.width * 0.34, block.height * 0.08)
        margin_y = max(10.0, block.height * 0.16, block.width * 0.5)
    else:
        margin_x = max(10.0, block.width * 0.1, block.height * 0.44)
        margin_y = max(8.0, block.height * 0.34, block.width * 0.05)

    x = max(block.x - crop_x - margin_x, 0.0)
    y = max(block.y - crop_y - margin_y, 0.0)
    width = min(block.width + (margin_x * 2.0), crop_width - x)
    height = min(block.height + (margin_y * 2.0), crop_height - y)
    return {
        "x": x,
        "y": y,
        "width": max(width, 1.0),
        "height": max(height, 1.0),
    }


def _component_is_probably_border_art(
    *,
    component_box: dict[str, float],
    crop_width: int,
    crop_height: int,
) -> bool:
    touches_boundary = (
        component_box["x"] <= 1.0
        or component_box["y"] <= 1.0
        or (component_box["x"] + component_box["width"]) >= (crop_width - 1.0)
        or (component_box["y"] + component_box["height"]) >= (crop_height - 1.0)
    )
    if not touches_boundary:
        return False

    is_long_horizontal = component_box["width"] >= max(crop_width * 0.42, component_box["height"] * 5.5)
    is_long_vertical = component_box["height"] >= max(crop_height * 0.42, component_box["width"] * 5.5)
    return is_long_horizontal or is_long_vertical


def _component_is_relevant_for_text_area(
    *,
    component_box: dict[str, float],
    anchor_box: dict[str, float],
    block: ComicTextBlock,
) -> bool:
    if _bounding_box_iou(component_box, anchor_box) > 0.0:
        return True

    component_center_x = component_box["x"] + (component_box["width"] / 2.0)
    component_center_y = component_box["y"] + (component_box["height"] / 2.0)
    anchor_center_x = anchor_box["x"] + (anchor_box["width"] / 2.0)
    anchor_center_y = anchor_box["y"] + (anchor_box["height"] / 2.0)
    max_dx = max(anchor_box["width"] * 0.6, block.width * 1.1, 18.0)
    max_dy = max(anchor_box["height"] * 0.6, block.height * 0.28, 18.0)
    if block.vertical:
        max_dx = max(max_dx, block.width * 1.6, 22.0)
        max_dy = max(max_dy, block.height * 0.5, 26.0)
    else:
        max_dx = max(max_dx, block.width * 0.38, 22.0)
        max_dy = max(max_dy, block.height * 1.4, 22.0)

    return (
        abs(component_center_x - anchor_center_x) <= max_dx
        and abs(component_center_y - anchor_center_y) <= max_dy
    )


def _build_relevant_text_component_bounds(
    *,
    mask: np.ndarray,
    anchor_box: dict[str, float],
    block: ComicTextBlock,
) -> dict[str, float] | None:
    if mask.size == 0 or np.count_nonzero(mask) == 0:
        return None

    component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if component_count <= 1:
        return None

    relevant_bounds: dict[str, float] | None = None
    mask_height, mask_width = mask.shape
    for component_index in range(1, component_count):
        area = int(stats[component_index, cv2.CC_STAT_AREA])
        if area < 3:
            continue

        component_box = {
            "x": float(stats[component_index, cv2.CC_STAT_LEFT]),
            "y": float(stats[component_index, cv2.CC_STAT_TOP]),
            "width": float(stats[component_index, cv2.CC_STAT_WIDTH]),
            "height": float(stats[component_index, cv2.CC_STAT_HEIGHT]),
        }
        if _component_is_probably_border_art(
            component_box=component_box,
            crop_width=mask_width,
            crop_height=mask_height,
        ):
            continue
        if not _component_is_relevant_for_text_area(
            component_box=component_box,
            anchor_box=anchor_box,
            block=block,
        ):
            continue

        if relevant_bounds is None:
            relevant_bounds = component_box
            continue

        relevant_bounds = {
            "x": min(relevant_bounds["x"], component_box["x"]),
            "y": min(relevant_bounds["y"], component_box["y"]),
            "width": max(
                relevant_bounds["x"] + relevant_bounds["width"],
                component_box["x"] + component_box["width"],
            ) - min(relevant_bounds["x"], component_box["x"]),
            "height": max(
                relevant_bounds["y"] + relevant_bounds["height"],
                component_box["y"] + component_box["height"],
            ) - min(relevant_bounds["y"], component_box["y"]),
        }

    return relevant_bounds


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
    deduplicated = _refine_candidate_context_areas(
        deduplicated,
        page_width=page_width,
        page_height=page_height,
    )
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
    text_area = _build_text_area_from_cluster(
        cluster=cluster,
        page_width=page_width,
        page_height=page_height,
    )
    padding_x = min(48.0, max(14.0, median_width * 1.15))
    padding_y = min(56.0, max(14.0, median_height * 0.8))
    context_area = _clamp_bounding_box(
        x=min_x - padding_x,
        y=min_y - padding_y,
        width=cluster_width + (padding_x * 2),
        height=cluster_height + (padding_y * 2),
        page_width=page_width,
        page_height=page_height,
    )

    box_area = context_area["width"] * context_area["height"]
    if box_area < 1200:
        return None
    if box_area > page_width * page_height * 0.22:
        return None
    if box_count == 1 and box_area < 2600:
        return None

    region_type = _classify_cluster(cluster, context_area)
    average_confidence = sum(text_box.confidence for text_box in cluster) / box_count
    confidence = min(0.98, round((average_confidence * 0.92) + 0.06, 2))
    return DetectedRegionCandidate(
        type=region_type,
        confidence=confidence,
        bounding_box=text_area,
        text_area=text_area,
        context_area=context_area,
    )


def _build_text_area_from_cluster(
    *,
    cluster: list[RecognizedTextBox],
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    min_x = min(text_box.x for text_box in cluster)
    min_y = min(text_box.y for text_box in cluster)
    max_x = max(text_box.x + text_box.width for text_box in cluster)
    max_y = max(text_box.y + text_box.height for text_box in cluster)
    median_width = median(text_box.width for text_box in cluster)
    median_height = median(text_box.height for text_box in cluster)
    padding_x = min(12.0, max(3.0, median_width * 0.18))
    padding_y = min(12.0, max(3.0, median_height * 0.14))
    return _clamp_bounding_box(
        x=min_x - padding_x,
        y=min_y - padding_y,
        width=(max_x - min_x) + (padding_x * 2),
        height=(max_y - min_y) + (padding_y * 2),
        page_width=page_width,
        page_height=page_height,
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


def _classify_comic_text_block(
    *,
    block: ComicTextBlock,
    bounding_box: dict[str, float],
    fitted_from_container: bool,
    page_width: int,
    page_height: int,
) -> str:
    width = bounding_box["width"]
    height = bounding_box["height"]
    text_density = (block.width * block.height) / max(width * height, 1.0)
    touches_page_edge = _touches_page_edge(
        bounding_box=bounding_box,
        page_width=page_width,
        page_height=page_height,
    )

    if (
        block.vertical
        and touches_page_edge
        and width <= min(118.0, page_width * 0.1)
        and height >= max(220.0, page_height * 0.18)
    ):
        return "free_text"
    if (
        block.vertical
        and touches_page_edge
        and text_density >= 0.33
        and width <= block.width * 2.8
        and height <= block.height * 1.55
    ):
        return "free_text"
    if (
        not fitted_from_container
        and not block.vertical
        and width >= height * 1.35
        and width < 220
        and height < 120
    ):
        return "free_text"
    if not block.vertical and width >= height * 1.1:
        return "narration_box"
    if width <= height * 0.72:
        return "speech_balloon"
    return "speech_balloon"


def _touches_page_edge(
    *,
    bounding_box: dict[str, float],
    page_width: int,
    page_height: int,
    margin: float = 12.0,
) -> bool:
    return (
        bounding_box["x"] <= margin
        or bounding_box["y"] <= margin
        or bounding_box["x"] + bounding_box["width"] >= page_width - margin
        or bounding_box["y"] + bounding_box["height"] >= page_height - margin
    )


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


def _refine_candidate_context_areas(
    candidates: list[DetectedRegionCandidate],
    *,
    page_width: int,
    page_height: int,
) -> list[DetectedRegionCandidate]:
    refined = [
        _refine_single_candidate_context_area(
            candidate,
            page_width=page_width,
            page_height=page_height,
        )
        for candidate in candidates
    ]
    return _resolve_overlapping_speech_balloon_context_areas(
        refined,
        page_width=page_width,
        page_height=page_height,
    )


def _refine_single_candidate_context_area(
    candidate: DetectedRegionCandidate,
    *,
    page_width: int,
    page_height: int,
) -> DetectedRegionCandidate:
    text_area = candidate.text_area or candidate.bounding_box
    if candidate.type == "narration_box":
        padding_x = min(32.0, max(14.0, text_area["width"] * 0.05, text_area["height"] * 0.62))
        padding_y = min(20.0, max(8.0, text_area["height"] * 0.34, text_area["width"] * 0.012))
        return replace(
            candidate,
            context_area=_build_context_box_around_text(
                text_area=text_area,
                padding_x=padding_x,
                padding_y=padding_y,
                page_width=page_width,
                page_height=page_height,
            ),
        )

    if candidate.type == "free_text":
        padding_x = min(24.0, max(8.0, text_area["width"] * 0.18, text_area["height"] * 0.08))
        padding_y = min(28.0, max(12.0, text_area["height"] * 0.12, text_area["width"] * 0.08))
        return replace(
            candidate,
            context_area=_build_context_box_around_text(
                text_area=text_area,
                padding_x=padding_x,
                padding_y=padding_y,
                page_width=page_width,
                page_height=page_height,
            ),
        )

    if candidate.type == "speech_balloon":
        return replace(
            candidate,
            context_area=_normalize_speech_balloon_context_area(
                context_area=candidate.context_area or candidate.bounding_box,
                text_area=text_area,
                page_width=page_width,
                page_height=page_height,
            ),
        )

    return candidate


def _build_context_box_around_text(
    *,
    text_area: dict[str, float],
    padding_x: float,
    padding_y: float,
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    return _clamp_bounding_box(
        x=text_area["x"] - padding_x,
        y=text_area["y"] - padding_y,
        width=text_area["width"] + (padding_x * 2.0),
        height=text_area["height"] + (padding_y * 2.0),
        page_width=page_width,
        page_height=page_height,
    )


def _resolve_overlapping_speech_balloon_context_areas(
    candidates: list[DetectedRegionCandidate],
    *,
    page_width: int,
    page_height: int,
) -> list[DetectedRegionCandidate]:
    refined = list(candidates)
    for _pass in range(3):
        changed = False
        for left_index in range(len(refined)):
            for right_index in range(left_index + 1, len(refined)):
                next_pair = _shrink_overlapping_speech_context_pair(
                    left=refined[left_index],
                    right=refined[right_index],
                    page_width=page_width,
                    page_height=page_height,
                )
                if next_pair is None:
                    continue
                next_left, next_right = next_pair
                if (
                    next_left.context_area != refined[left_index].context_area
                    or next_right.context_area != refined[right_index].context_area
                ):
                    refined[left_index] = next_left
                    refined[right_index] = next_right
                    changed = True
        if not changed:
            break
    return refined


def _shrink_overlapping_speech_context_pair(
    *,
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
    page_width: int,
    page_height: int,
) -> tuple[DetectedRegionCandidate, DetectedRegionCandidate] | None:
    if left.type != "speech_balloon" or right.type != "speech_balloon":
        return None

    left_context = left.context_area or left.bounding_box
    right_context = right.context_area or right.bounding_box
    overlap_x = _axis_overlap(
        left_context["x"],
        left_context["x"] + left_context["width"],
        right_context["x"],
        right_context["x"] + right_context["width"],
    )
    overlap_y = _axis_overlap(
        left_context["y"],
        left_context["y"] + left_context["height"],
        right_context["y"],
        right_context["y"] + right_context["height"],
    )
    if overlap_x < 14.0 or overlap_y < 14.0:
        return None

    old_overlap_area = overlap_x * overlap_y
    minimum_area = max(
        min(
            left_context["width"] * left_context["height"],
            right_context["width"] * right_context["height"],
        ),
        1.0,
    )
    if (old_overlap_area / minimum_area) < 0.05:
        return None

    next_left_box, next_right_box = _choose_best_speech_context_split(
        left=left,
        right=right,
        split_x=_split_speech_context_pair_along_x(
            left=left,
            right=right,
            page_width=page_width,
            page_height=page_height,
        ),
        split_y=_split_speech_context_pair_along_y(
            left=left,
            right=right,
            page_width=page_width,
            page_height=page_height,
        ),
    )

    new_overlap_area = _bounding_box_intersection_area(next_left_box, next_right_box)
    if new_overlap_area >= (old_overlap_area - 24.0):
        return None

    return (
        replace(left, context_area=next_left_box),
        replace(right, context_area=next_right_box),
    )


def _choose_speech_context_split_axis(
    *,
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
) -> str:
    left_text = left.text_area or left.bounding_box
    right_text = right.text_area or right.bounding_box
    left_context = left.context_area or left.bounding_box
    right_context = right.context_area or right.bounding_box

    center_dx = abs(_bounding_box_center_x(left_text) - _bounding_box_center_x(right_text))
    center_dy = abs(_bounding_box_center_y(left_text) - _bounding_box_center_y(right_text))
    normalized_dx = center_dx / max(min(left_context["width"], right_context["width"]), 1.0)
    normalized_dy = center_dy / max(min(left_context["height"], right_context["height"]), 1.0)
    return "x" if normalized_dx >= normalized_dy else "y"


def _choose_best_speech_context_split(
    *,
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
    split_x: tuple[dict[str, float], dict[str, float]],
    split_y: tuple[dict[str, float], dict[str, float]],
) -> tuple[dict[str, float], dict[str, float]]:
    preferred_axis = _choose_speech_context_split_axis(left=left, right=right)
    left_context = left.context_area or left.bounding_box
    right_context = right.context_area or right.bounding_box

    def score_split(
        split_pair: tuple[dict[str, float], dict[str, float]],
    ) -> tuple[float, float]:
        split_left, split_right = split_pair
        overlap_area = _bounding_box_intersection_area(split_left, split_right)
        total_area_loss = (
            (left_context["width"] * left_context["height"]) - (split_left["width"] * split_left["height"])
        ) + (
            (right_context["width"] * right_context["height"]) - (split_right["width"] * split_right["height"])
        )
        return overlap_area, total_area_loss

    score_x = score_split(split_x)
    score_y = score_split(split_y)
    if score_x[0] < score_y[0]:
        return split_x
    if score_y[0] < score_x[0]:
        return split_y
    if score_x[1] < score_y[1]:
        return split_x
    if score_y[1] < score_x[1]:
        return split_y
    return split_x if preferred_axis == "x" else split_y


def _split_speech_context_pair_along_x(
    *,
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
    page_width: int,
    page_height: int,
) -> tuple[dict[str, float], dict[str, float]]:
    left_text = left.text_area or left.bounding_box
    right_text = right.text_area or right.bounding_box
    left_context = left.context_area or left.bounding_box
    right_context = right.context_area or right.bounding_box
    if _bounding_box_center_x(left_text) > _bounding_box_center_x(right_text):
        left_text, right_text = right_text, left_text
        left_context, right_context = right_context, left_context
        swapped = True
    else:
        swapped = False

    cut_x = (_bounding_box_center_x(left_text) + _bounding_box_center_x(right_text)) / 2.0
    guard_padding = min(
        28.0,
        max(
            12.0,
            min(left_text["width"], right_text["width"]) * 0.2,
            min(left_text["height"], right_text["height"]) * 0.08,
        ),
    )

    left_guard_x2 = left_text["x"] + left_text["width"] + guard_padding
    right_guard_x1 = right_text["x"] - guard_padding
    left_x2 = max(
        min(left_context["x"] + left_context["width"], cut_x + guard_padding),
        left_guard_x2,
    )
    right_x1 = min(
        max(right_context["x"], cut_x - guard_padding),
        right_guard_x1,
    )

    next_left = _normalize_speech_balloon_context_area(
        context_area=_clamp_bounding_box(
            x=left_context["x"],
            y=left_context["y"],
            width=max(left_x2 - left_context["x"], 1.0),
            height=left_context["height"],
            page_width=page_width,
            page_height=page_height,
        ),
        text_area=left_text,
        page_width=page_width,
        page_height=page_height,
    )
    next_right = _normalize_speech_balloon_context_area(
        context_area=_clamp_bounding_box(
            x=right_x1,
            y=right_context["y"],
            width=max((right_context["x"] + right_context["width"]) - right_x1, 1.0),
            height=right_context["height"],
            page_width=page_width,
            page_height=page_height,
        ),
        text_area=right_text,
        page_width=page_width,
        page_height=page_height,
    )

    if swapped:
        return next_right, next_left
    return next_left, next_right


def _split_speech_context_pair_along_y(
    *,
    left: DetectedRegionCandidate,
    right: DetectedRegionCandidate,
    page_width: int,
    page_height: int,
) -> tuple[dict[str, float], dict[str, float]]:
    left_text = left.text_area or left.bounding_box
    right_text = right.text_area or right.bounding_box
    left_context = left.context_area or left.bounding_box
    right_context = right.context_area or right.bounding_box
    if _bounding_box_center_y(left_text) > _bounding_box_center_y(right_text):
        left_text, right_text = right_text, left_text
        left_context, right_context = right_context, left_context
        swapped = True
    else:
        swapped = False

    cut_y = (_bounding_box_center_y(left_text) + _bounding_box_center_y(right_text)) / 2.0
    guard_padding = min(
        28.0,
        max(
            12.0,
            min(left_text["height"], right_text["height"]) * 0.12,
            min(left_text["width"], right_text["width"]) * 0.22,
        ),
    )

    top_guard_y2 = left_text["y"] + left_text["height"] + guard_padding
    bottom_guard_y1 = right_text["y"] - guard_padding
    top_y2 = max(
        min(left_context["y"] + left_context["height"], cut_y + guard_padding),
        top_guard_y2,
    )
    bottom_y1 = min(
        max(right_context["y"], cut_y - guard_padding),
        bottom_guard_y1,
    )

    next_top = _normalize_speech_balloon_context_area(
        context_area=_clamp_bounding_box(
            x=left_context["x"],
            y=left_context["y"],
            width=left_context["width"],
            height=max(top_y2 - left_context["y"], 1.0),
            page_width=page_width,
            page_height=page_height,
        ),
        text_area=left_text,
        page_width=page_width,
        page_height=page_height,
    )
    next_bottom = _normalize_speech_balloon_context_area(
        context_area=_clamp_bounding_box(
            x=right_context["x"],
            y=bottom_y1,
            width=right_context["width"],
            height=max((right_context["y"] + right_context["height"]) - bottom_y1, 1.0),
            page_width=page_width,
            page_height=page_height,
        ),
        text_area=right_text,
        page_width=page_width,
        page_height=page_height,
    )

    if swapped:
        return next_bottom, next_top
    return next_top, next_bottom


def _normalize_speech_balloon_context_area(
    *,
    context_area: dict[str, float],
    text_area: dict[str, float],
    page_width: int,
    page_height: int,
) -> dict[str, float]:
    is_vertical = text_area["height"] >= text_area["width"] * 1.12
    left_padding = max(text_area["x"] - context_area["x"], 0.0)
    right_padding = max(
        (context_area["x"] + context_area["width"]) - (text_area["x"] + text_area["width"]),
        0.0,
    )
    top_padding = max(text_area["y"] - context_area["y"], 0.0)
    bottom_padding = max(
        (context_area["y"] + context_area["height"]) - (text_area["y"] + text_area["height"]),
        0.0,
    )

    if is_vertical:
        max_padding_x = min(82.0, max(24.0, text_area["width"] * 1.25, text_area["height"] * 0.5))
        max_padding_y = min(68.0, max(18.0, text_area["height"] * 0.55, text_area["width"] * 1.2))
        asymmetry_bias_x = 1.6
        asymmetry_bias_y = 1.8
        asymmetry_offset_x = 9.0
        asymmetry_offset_y = 10.0
    else:
        max_padding_x = min(52.0, max(14.0, text_area["width"] * 0.24, text_area["height"] * 0.5))
        max_padding_y = min(44.0, max(14.0, text_area["height"] * 0.34, text_area["width"] * 0.16))
        asymmetry_bias_x = 1.8
        asymmetry_bias_y = 1.6
        asymmetry_offset_x = 10.0
        asymmetry_offset_y = 12.0

    left_padding, right_padding = _rebalance_edge_paddings(
        left_padding,
        right_padding,
        max_padding=max_padding_x,
        asymmetry_bias=asymmetry_bias_x,
        asymmetry_offset=asymmetry_offset_x,
    )
    top_padding, bottom_padding = _rebalance_edge_paddings(
        top_padding,
        bottom_padding,
        max_padding=max_padding_y,
        asymmetry_bias=asymmetry_bias_y,
        asymmetry_offset=asymmetry_offset_y,
    )

    return _clamp_bounding_box(
        x=text_area["x"] - left_padding,
        y=text_area["y"] - top_padding,
        width=text_area["width"] + left_padding + right_padding,
        height=text_area["height"] + top_padding + bottom_padding,
        page_width=page_width,
        page_height=page_height,
    )


def _rebalance_edge_paddings(
    leading_padding: float,
    trailing_padding: float,
    *,
    max_padding: float,
    asymmetry_bias: float,
    asymmetry_offset: float,
) -> tuple[float, float]:
    leading = min(leading_padding, max_padding)
    trailing = min(trailing_padding, max_padding)
    if leading > (trailing * asymmetry_bias) + asymmetry_offset:
        leading = min(max_padding, (trailing * asymmetry_bias) + asymmetry_offset)
    if trailing > (leading * asymmetry_bias) + asymmetry_offset:
        trailing = min(max_padding, (leading * asymmetry_bias) + asymmetry_offset)
    return max(leading, 0.0), max(trailing, 0.0)


def _bounding_box_center_x(bounding_box: dict[str, float]) -> float:
    return bounding_box["x"] + (bounding_box["width"] / 2.0)


def _bounding_box_center_y(bounding_box: dict[str, float]) -> float:
    return bounding_box["y"] + (bounding_box["height"] / 2.0)


def _bounding_box_intersection_area(
    left: dict[str, float],
    right: dict[str, float],
) -> float:
    overlap_x = _axis_overlap(
        left["x"],
        left["x"] + left["width"],
        right["x"],
        right["x"] + right["width"],
    )
    overlap_y = _axis_overlap(
        left["y"],
        left["y"] + left["height"],
        right["y"],
        right["y"] + right["height"],
    )
    return overlap_x * overlap_y


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


def _bounding_box_iou(
    left_box: dict[str, float],
    right_box: dict[str, float],
) -> float:
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


def _annotate_cleanup_candidates(
    *,
    asset_path: Path,
    candidates: list[DetectedRegionCandidate],
) -> list[DetectedRegionCandidate]:
    if len(candidates) == 0:
        return []

    grayscale = cv2.imdecode(np.fromfile(str(asset_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if grayscale is None:
        return candidates

    annotated: list[DetectedRegionCandidate] = []
    for candidate in candidates:
        cleanup_strategy, cleanup_confidence = _classify_cleanup_strategy(
            grayscale_image=grayscale,
            candidate=candidate,
        )
        annotated.append(
            replace(
                candidate,
                cleanup_strategy=cleanup_strategy,
                cleanup_confidence=cleanup_confidence,
            )
        )
    return annotated


def _classify_cleanup_strategy(
    *,
    grayscale_image: np.ndarray,
    candidate: DetectedRegionCandidate,
) -> tuple[str, float]:
    if candidate.type == "free_text":
        return "background_reconstruction", 0.91

    box = candidate.bounding_box
    x1 = max(int(round(box["x"])), 0)
    y1 = max(int(round(box["y"])), 0)
    x2 = min(int(round(box["x"] + box["width"])), grayscale_image.shape[1])
    y2 = min(int(round(box["y"] + box["height"])), grayscale_image.shape[0])
    if x2 <= x1 or y2 <= y1:
        return "background_reconstruction", 0.5

    crop = grayscale_image[y1:y2, x1:x2]
    blurred = cv2.GaussianBlur(crop, (0, 0), sigmaX=3.0, sigmaY=3.0)
    std_deviation = float(np.std(blurred))
    bright_ratio = float(np.mean(blurred >= 210))
    dark_ratio = float(np.mean(blurred <= 90))
    edge_density = float(np.mean(cv2.Canny(blurred, 80, 160) > 0))

    solid_fill_score = 0.0
    solid_fill_score += _normalize_metric(bright_ratio, low=0.34, high=0.78) * 0.46
    solid_fill_score += _normalize_metric(38.0 - std_deviation, low=0.0, high=26.0) * 0.28
    solid_fill_score += _normalize_metric(0.12 - edge_density, low=0.0, high=0.09) * 0.18
    solid_fill_score += _normalize_metric(0.18 - dark_ratio, low=0.0, high=0.14) * 0.08
    if candidate.type in {"speech_balloon", "narration_box"}:
        solid_fill_score = min(solid_fill_score + 0.06, 1.0)
    solid_fill_score = max(0.0, min(solid_fill_score, 1.0))

    if solid_fill_score >= 0.56:
        confidence = round(max(0.55, min(0.98, 0.52 + (solid_fill_score * 0.46))), 2)
        return "solid_fill", confidence

    reconstruct_confidence = round(max(0.55, min(0.98, 0.52 + ((1.0 - solid_fill_score) * 0.46))), 2)
    return "background_reconstruction", reconstruct_confidence


def _normalize_metric(value: float, *, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return (value - low) / (high - low)


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


def _decode_grayscale_image(asset_bytes: bytes) -> np.ndarray | None:
    if len(asset_bytes) == 0:
        return None
    return cv2.imdecode(np.frombuffer(asset_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
