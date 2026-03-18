from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class CleanupMaskSpec:
    cleanup_strategy: str
    points: tuple[tuple[float, float], ...]


def render_cleaned_png(
    *,
    source_bytes: bytes,
    masks: list[CleanupMaskSpec],
) -> bytes | None:
    image = cv2.imdecode(np.frombuffer(source_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        return None

    working_image, alpha_channel = _normalize_image(image)
    if len(masks) == 0:
        encoded = _encode_png(_restore_alpha_channel(working_image, alpha_channel))
        return encoded

    ordered_masks = sorted(
        masks,
        key=lambda mask: 0 if mask.cleanup_strategy == "background_reconstruction" else 1,
    )
    for mask in ordered_masks:
        polygon_mask = _build_polygon_mask(
            image_height=working_image.shape[0],
            image_width=working_image.shape[1],
            points=mask.points,
        )
        if np.count_nonzero(polygon_mask) == 0:
            continue

        if mask.cleanup_strategy == "background_reconstruction":
            working_image = _apply_background_reconstruction(working_image, polygon_mask)
            continue

        working_image = _apply_solid_fill(working_image, polygon_mask)

    encoded = _encode_png(_restore_alpha_channel(working_image, alpha_channel))
    return encoded


def _normalize_image(image: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), None

    if image.shape[2] == 4:
        return image[:, :, :3].copy(), image[:, :, 3].copy()

    return image.copy(), None


def _restore_alpha_channel(image: np.ndarray, alpha_channel: np.ndarray | None) -> np.ndarray:
    if alpha_channel is None:
        return image
    return np.dstack((image, alpha_channel))


def _build_polygon_mask(
    *,
    image_height: int,
    image_width: int,
    points: tuple[tuple[float, float], ...],
) -> np.ndarray:
    polygon_points = np.array(
        [
            [
                int(round(min(max(point[0], 0.0), image_width - 1))),
                int(round(min(max(point[1], 0.0), image_height - 1))),
            ]
            for point in points
        ],
        dtype=np.int32,
    )
    mask = np.zeros((image_height, image_width), dtype=np.uint8)
    if len(polygon_points) < 4:
        return mask
    cv2.fillPoly(mask, [polygon_points], 255)
    return mask


def _apply_background_reconstruction(image: np.ndarray, polygon_mask: np.ndarray) -> np.ndarray:
    expanded_mask = _expand_mask(polygon_mask, radius=2)
    return cv2.inpaint(image, expanded_mask, 3.0, cv2.INPAINT_TELEA)


def _apply_solid_fill(image: np.ndarray, polygon_mask: np.ndarray) -> np.ndarray:
    expanded_mask = _expand_mask(polygon_mask, radius=1)
    fill_color = _estimate_fill_color(image, expanded_mask)
    next_image = image.copy()
    next_image[expanded_mask > 0] = fill_color
    return next_image


def _expand_mask(mask: np.ndarray, *, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    kernel_size = max((radius * 2) + 1, 3)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.dilate(mask, kernel, iterations=1)


def _estimate_fill_color(image: np.ndarray, polygon_mask: np.ndarray) -> np.ndarray:
    sample_ring = _build_sample_ring(polygon_mask)
    ring_samples = image[sample_ring > 0]
    inner_samples = image[polygon_mask > 0]
    if ring_samples.size == 0 and inner_samples.size == 0:
        return np.array([255, 255, 255], dtype=np.uint8)

    if image.ndim == 2:
        return _estimate_grayscale_fill_color(
            ring_samples=ring_samples,
            inner_samples=inner_samples,
        )

    channel_values = _estimate_rgb_fill_color(
        ring_samples=ring_samples,
        inner_samples=inner_samples,
    )
    return np.clip(channel_values, 0, 255).astype(np.uint8)


def _estimate_grayscale_fill_color(
    *,
    ring_samples: np.ndarray,
    inner_samples: np.ndarray,
) -> np.ndarray:
    if ring_samples.size == 0:
        dominant_value = int(np.percentile(inner_samples, 98))
    elif inner_samples.size == 0:
        dominant_value = int(np.percentile(ring_samples, 96))
    else:
        dominant_value = int(
            max(
                np.percentile(ring_samples, 96),
                np.percentile(inner_samples, 98),
            )
        )

    if dominant_value >= 236:
        dominant_value = 255
    return np.array([dominant_value, dominant_value, dominant_value], dtype=np.uint8)


def _estimate_rgb_fill_color(
    *,
    ring_samples: np.ndarray,
    inner_samples: np.ndarray,
) -> np.ndarray:
    if ring_samples.size == 0:
        channel_values = np.percentile(inner_samples, 98, axis=0)
    elif inner_samples.size == 0:
        channel_values = np.percentile(ring_samples, 96, axis=0)
    else:
        channel_values = np.maximum(
            np.percentile(ring_samples, 96, axis=0),
            np.percentile(inner_samples, 98, axis=0),
        )

    mean_brightness = float(np.mean(channel_values))
    color_spread = float(np.max(channel_values) - np.min(channel_values))

    if inner_samples.size > 0:
        white_candidate = np.percentile(inner_samples, 99, axis=0)
    else:
        white_candidate = np.percentile(ring_samples, 98, axis=0)
    white_brightness = float(np.mean(white_candidate))
    white_spread = float(np.max(white_candidate) - np.min(white_candidate))

    brightness_samples = []
    if ring_samples.size > 0:
        brightness_samples.append(np.mean(ring_samples, axis=1))
    if inner_samples.size > 0:
        brightness_samples.append(np.mean(inner_samples, axis=1))
    combined_brightness = (
        np.concatenate(brightness_samples)
        if len(brightness_samples) > 0
        else np.array([], dtype=np.float32)
    )
    bright_ratio = (
        float(np.mean(combined_brightness >= 238))
        if combined_brightness.size > 0
        else 0.0
    )

    if white_brightness >= 240 and white_spread <= 18:
        return np.array([255, 255, 255], dtype=np.uint8)

    if mean_brightness >= 236 and color_spread <= 14:
        return np.array([255, 255, 255], dtype=np.uint8)

    if bright_ratio >= 0.35 and white_brightness >= 234 and white_spread <= 22:
        return np.array([255, 255, 255], dtype=np.uint8)

    if mean_brightness >= 232 and color_spread <= 12:
        snapped_value = int(min(255, round(mean_brightness + 10)))
        return np.array([snapped_value, snapped_value, snapped_value], dtype=np.uint8)

    return channel_values


def _build_sample_ring(mask: np.ndarray) -> np.ndarray:
    outer_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    inner_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    outer = cv2.dilate(mask, outer_kernel, iterations=1)
    inner = cv2.dilate(mask, inner_kernel, iterations=1)
    return cv2.subtract(outer, inner)


def _encode_png(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Could not encode cleaned preview to PNG.")
    return encoded.tobytes()


def build_cleanup_mask_specs(
    *,
    approved_masks: list[dict[str, Any]],
    region_lookup: dict[str, dict[str, Any]],
) -> list[CleanupMaskSpec]:
    cleanup_masks: list[CleanupMaskSpec] = []
    for approved_mask in approved_masks:
        region_id = str(approved_mask.get("region_id") or "")
        region = region_lookup.get(region_id, {})
        shape = approved_mask.get("shape")
        if not isinstance(shape, dict):
            continue
        points = shape.get("points")
        if not isinstance(points, list):
            continue
        cleanup_strategy = str(region.get("cleanup_strategy") or "solid_fill")
        cleanup_masks.append(
            CleanupMaskSpec(
                cleanup_strategy=cleanup_strategy,
                points=tuple(
                    (
                        float(point.get("x") or 0.0),
                        float(point.get("y") or 0.0),
                    )
                    for point in points
                    if isinstance(point, dict)
                ),
            )
        )
    return cleanup_masks
