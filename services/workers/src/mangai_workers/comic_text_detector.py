from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import torch

from mangai_workers.vendor.comic_text_detector.inference import TextDetector


if TYPE_CHECKING:
    from mangai_workers.config import WorkerSettings


class DetectionProviderError(Exception):
    pass


@dataclass(frozen=True)
class ComicTextBlock:
    x: float
    y: float
    width: float
    height: float
    language: str
    vertical: bool


def extract_comic_text_detector_blocks(
    *,
    asset_path: Path,
    settings: WorkerSettings,
) -> list[ComicTextBlock]:
    if not asset_path.exists():
        raise FileNotFoundError(f"Could not find comic text detection asset '{asset_path}'.")

    model_path = settings.comic_text_detector_model_path
    if model_path is None or not model_path.exists():
        raise DetectionProviderError(
            "Comic text detector requires a valid MANGAI_COMIC_TEXT_DETECTOR_MODEL_PATH."
        )

    image = _read_image(asset_path)
    try:
        detector = _get_cached_text_detector(
            model_path=str(model_path),
            device=_pick_device(model_path),
        )
    except Exception as exc:  # noqa: BLE001 - runtime bootstrap failures must be recoverable
        raise DetectionProviderError(
            "Comic text detector could not initialize in the current worker runtime."
        ) from exc

    try:
        _mask, _refined_mask, blocks = detector(image, keep_undetected_mask=True)
    except Exception as exc:  # noqa: BLE001 - provider/runtime failures should be recoverable
        raise DetectionProviderError("Comic text detector could not process the current asset.") from exc

    normalized_blocks: list[ComicTextBlock] = []
    for block in blocks:
        xyxy = getattr(block, "xyxy", None)
        if xyxy is None or len(xyxy) != 4:
            continue

        x1, y1, x2, y2 = [int(value) for value in xyxy]
        width = max(float(x2 - x1), 1.0)
        height = max(float(y2 - y1), 1.0)
        if width < 8.0 or height < 8.0:
            continue

        normalized_blocks.append(
            ComicTextBlock(
                x=float(x1),
                y=float(y1),
                width=width,
                height=height,
                language=str(getattr(block, "language", "unknown") or "unknown"),
                vertical=bool(getattr(block, "vertical", False)),
            )
        )

    return normalized_blocks


def _read_image(asset_path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(str(asset_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise DetectionProviderError(f"Comic text detector could not decode '{asset_path.name}'.")
    return image


def _pick_device(model_path: Path) -> str:
    if model_path.suffix.lower() == ".onnx":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=4)
def _get_cached_text_detector(*, model_path: str, device: str) -> TextDetector:
    return TextDetector(model_path=model_path, input_size=1024, device=device)
