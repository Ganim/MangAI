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
    if (old_overlap_area / minimum_area) < 0.08:
        return None

    split_axis = _choose_speech_context_split_axis(left=left, right=right)
    if split_axis == "x":
        next_left_box, next_right_box = _split_speech_context_pair_along_x(
            left=left,
            right=right,
            page_width=page_width,
            page_height=page_height,
        )
    else:
        next_left_box, next_right_box = _split_speech_context_pair_along_y(
            left=left,
            right=right,
            page_width=page_width,
            page_height=page_height,
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

    next_left = _clamp_bounding_box(
        x=left_context["x"],
        y=left_context["y"],
        width=max(left_x2 - left_context["x"], 1.0),
        height=left_context["height"],
        page_width=page_width,
        page_height=page_height,
    )
    next_right = _clamp_bounding_box(
        x=right_x1,
        y=right_context["y"],
        width=max((right_context["x"] + right_context["width"]) - right_x1, 1.0),
        height=right_context["height"],
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

    next_top = _clamp_bounding_box(
        x=left_context["x"],
        y=left_context["y"],
        width=left_context["width"],
        height=max(top_y2 - left_context["y"], 1.0),
        page_width=page_width,
        page_height=page_height,
    )
    next_bottom = _clamp_bounding_box(
        x=right_context["x"],
        y=bottom_y1,
        width=right_context["width"],
        height=max((right_context["y"] + right_context["height"]) - bottom_y1, 1.0),
        page_width=page_width,
        page_height=page_height,
    )

    if swapped:
        return next_bottom, next_top
    return next_top, next_bottom


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
