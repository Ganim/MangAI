from mangai_workers.config import WorkerSettings
from mangai_workers.comic_text_detector import ComicTextBlock
from mangai_workers.detection import (
    DetectedRegionCandidate,
    _classify_cleanup_strategy,
    build_detected_regions_from_comic_text_blocks,
    build_detected_regions_from_recognized_lines,
    detect_regions_from_asset,
)
from mangai_workers.ocr import RecognizedLine
import numpy as np


def test_detect_regions_from_asset_falls_back_deterministically_when_ocr_fails(
    tmp_path,
    monkeypatch,
) -> None:
    asset_path = tmp_path / "page-a.bin"
    asset_path.write_bytes(b"asset-a" * 32)

    def raise_ocr_provider_error(**_kwargs):
        raise RuntimeError("simulated OCR bootstrap failure")

    monkeypatch.setattr(
        "mangai_workers.detection.extract_paddle_recognized_lines",
        raise_ocr_provider_error,
    )

    first_run = detect_regions_from_asset(
        asset_path=asset_path,
        page_width=1600,
        page_height=2400,
        settings=WorkerSettings(cache_dir=tmp_path / "cache"),
    )
    second_run = detect_regions_from_asset(
        asset_path=asset_path,
        page_width=1600,
        page_height=2400,
        settings=WorkerSettings(cache_dir=tmp_path / "cache"),
    )

    assert first_run == second_run
    assert len(first_run) >= 2
    assert all(candidate.confidence >= 0.76 for candidate in first_run)


def test_build_detected_regions_groups_vertical_columns_into_dialogue_regions() -> None:
    candidates = build_detected_regions_from_recognized_lines(
        recognized_lines=[
            RecognizedLine("縦1", 0.95, x=120, y=170, width=30, height=140),
            RecognizedLine("縦2", 0.93, x=165, y=176, width=28, height=132),
            RecognizedLine("縦3", 0.92, x=210, y=170, width=30, height=136),
            RecognizedLine("縦4", 0.94, x=730, y=760, width=32, height=150),
            RecognizedLine("縦5", 0.9, x=776, y=766, width=30, height=142),
        ],
        page_width=1000,
        page_height=1400,
    )

    assert len(candidates) == 2
    assert all(candidate.type == "speech_balloon" for candidate in candidates)
    assert candidates[0].bounding_box["x"] < candidates[1].bounding_box["x"]


def test_build_detected_regions_classifies_horizontal_cluster_as_narration_box() -> None:
    candidates = build_detected_regions_from_recognized_lines(
        recognized_lines=[
            RecognizedLine("Narration A", 0.91, x=210, y=120, width=120, height=34),
            RecognizedLine("Narration B", 0.93, x=360, y=123, width=128, height=36),
            RecognizedLine("Narration C", 0.89, x=510, y=119, width=112, height=32),
        ],
        page_width=900,
        page_height=1200,
    )

    assert len(candidates) == 1
    assert candidates[0].type == "narration_box"
    assert candidates[0].bounding_box["width"] > candidates[0].bounding_box["height"]


def test_build_detected_regions_from_comic_text_blocks_preserves_panel_detector_boxes() -> None:
    candidates = build_detected_regions_from_comic_text_blocks(
        text_blocks=[
            ComicTextBlock(
                x=680,
                y=70,
                width=60,
                height=140,
                language="ja",
                vertical=True,
            ),
            ComicTextBlock(
                x=505,
                y=620,
                width=560,
                height=42,
                language="unknown",
                vertical=False,
            ),
        ],
        page_width=1130,
        page_height=1600,
    )

    assert len(candidates) == 2
    assert candidates[0].type == "speech_balloon"
    assert candidates[1].type == "narration_box"
    assert candidates[0].bounding_box["x"] < 680
    assert candidates[1].bounding_box["width"] > 560


def test_detect_regions_prefers_comic_text_detector_provider(monkeypatch, tmp_path) -> None:
    asset_path = tmp_path / "page-a.bin"
    asset_path.write_bytes(b"asset-a" * 32)

    monkeypatch.setattr(
        "mangai_workers.detection.extract_comic_text_detector_blocks",
        lambda **_kwargs: [
            ComicTextBlock(
                x=100,
                y=120,
                width=80,
                height=180,
                language="ja",
                vertical=True,
            ),
            ComicTextBlock(
                x=320,
                y=240,
                width=220,
                height=44,
                language="unknown",
                vertical=False,
            ),
        ],
    )
    monkeypatch.setattr(
        "mangai_workers.detection.extract_paddle_recognized_lines",
        lambda **_kwargs: [],
    )

    candidates = detect_regions_from_asset(
        asset_path=asset_path,
        page_width=1000,
        page_height=1400,
        settings=WorkerSettings(
            cache_dir=tmp_path / "cache",
            detection_provider="comic_text_detector",
        ),
    )

    assert len(candidates) == 2
    assert candidates[0].type == "speech_balloon"
    assert candidates[1].type == "narration_box"


def test_classify_cleanup_strategy_prefers_solid_fill_for_clean_balloon_crop() -> None:
    image = np.full((220, 220), 245, dtype=np.uint8)
    image[70:150, 95:125] = 20
    candidate = DetectedRegionCandidate(
        type="speech_balloon",
        confidence=0.92,
        bounding_box={"x": 40, "y": 40, "width": 140, "height": 140},
    )

    strategy, confidence = _classify_cleanup_strategy(
        grayscale_image=image,
        candidate=candidate,
    )

    assert strategy == "solid_fill"
    assert confidence >= 0.55


def test_classify_cleanup_strategy_prefers_reconstruction_for_textured_crop() -> None:
    y, x = np.indices((220, 220))
    image = ((x * 7 + y * 11) % 255).astype(np.uint8)
    candidate = DetectedRegionCandidate(
        type="free_text",
        confidence=0.78,
        bounding_box={"x": 30, "y": 30, "width": 150, "height": 150},
    )

    strategy, confidence = _classify_cleanup_strategy(
        grayscale_image=image,
        candidate=candidate,
    )

    assert strategy == "background_reconstruction"
    assert confidence >= 0.55
