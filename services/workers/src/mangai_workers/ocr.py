from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import TYPE_CHECKING, Protocol
from urllib.request import Request, urlopen


if TYPE_CHECKING:
    from mangai_workers.config import WorkerSettings


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


@dataclass(frozen=True)
class RecognizedLine:
    text: str
    confidence: float
    x: float
    y: float


class OcrProviderError(Exception):
    pass


class OcrProvider(Protocol):
    def extract(
        self,
        *,
        asset_path: Path,
        source_language: str,
        regions: list[OcrCandidateRegion],
    ) -> list[OcrLine]: ...


OCR_FALLBACK_TEMPLATES = {
    "ja": "テキスト {index}",
    "ko": "텍스트 {index}",
    "zh": "文本 {index}",
    "en": "Text line {index}",
}

_open_url = urlopen


def extract_ocr_lines_from_asset(
    *,
    asset_path: Path,
    source_language: str,
    regions: list[OcrCandidateRegion],
    settings: WorkerSettings,
) -> list[OcrLine]:
    provider = build_ocr_provider(settings)
    try:
        return provider.extract(
            asset_path=asset_path,
            source_language=source_language,
            regions=regions,
        )
    except OcrProviderError:
        if settings.strict_provider_selection:
            raise
        return FallbackOcrProvider().extract(
            asset_path=asset_path,
            source_language=source_language,
            regions=regions,
        )


def build_ocr_provider(settings: WorkerSettings) -> OcrProvider:
    provider_name = settings.ocr_provider
    try:
        if provider_name == "fallback":
            return FallbackOcrProvider()
        if provider_name == "paddleocr":
            return PaddleOcrProvider()
        if provider_name == "azure_vision":
            return AzureVisionOcrProvider(settings)
        raise OcrProviderError(f"Unsupported OCR provider '{provider_name}'.")
    except OcrProviderError:
        if settings.strict_provider_selection:
            raise
        return FallbackOcrProvider()


class FallbackOcrProvider:
    def extract(
        self,
        *,
        asset_path: Path,
        source_language: str,
        regions: list[OcrCandidateRegion],
    ) -> list[OcrLine]:
        if not asset_path.exists():
            raise FileNotFoundError(f"Could not find OCR source asset '{asset_path}'.")
        return _build_fallback_lines(source_language=source_language, regions=regions)


class PaddleOcrProvider:
    def extract(
        self,
        *,
        asset_path: Path,
        source_language: str,
        regions: list[OcrCandidateRegion],
    ) -> list[OcrLine]:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrProviderError(
                "PaddleOCR is not installed in this worker environment."
            ) from exc

        if not asset_path.exists():
            raise FileNotFoundError(f"Could not find OCR source asset '{asset_path}'.")

        os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "BOS")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        ocr_engine = PaddleOCR(
            lang=_map_source_language_to_paddle(source_language),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        try:
            if hasattr(ocr_engine, "predict"):
                raw_result = ocr_engine.predict(input=str(asset_path))
                recognized_lines = _flatten_paddle_predict_output(raw_result)
            else:
                raw_result = ocr_engine.ocr(str(asset_path), cls=True)
                recognized_lines = _flatten_paddle_legacy_output(raw_result)
        except Exception as exc:  # noqa: BLE001 - optional dependency runtime failures should be recoverable
            raise OcrProviderError("PaddleOCR could not process the current asset.") from exc
        if len(recognized_lines) == 0:
            return _build_fallback_lines(source_language=source_language, regions=regions)
        return _group_recognized_lines_to_regions(
            source_language=source_language,
            regions=regions,
            recognized_lines=recognized_lines,
        )


class AzureVisionOcrProvider:
    def __init__(self, settings: WorkerSettings) -> None:
        self._read_url = settings.azure_vision_read_url
        self._api_key = settings.azure_vision_api_key
        self._timeout_seconds = settings.http_timeout_seconds
        self._poll_interval_seconds = settings.azure_vision_poll_interval_seconds

        if self._read_url is None or self._api_key is None:
            raise OcrProviderError(
                "Azure Vision OCR requires both MANGAI_AZURE_VISION_READ_URL and MANGAI_AZURE_VISION_API_KEY."
            )

    def extract(
        self,
        *,
        asset_path: Path,
        source_language: str,
        regions: list[OcrCandidateRegion],
    ) -> list[OcrLine]:
        if not asset_path.exists():
            raise FileNotFoundError(f"Could not find OCR source asset '{asset_path}'.")

        try:
            request = Request(
                self._read_url,
                data=asset_path.read_bytes(),
                headers={
                    "Ocp-Apim-Subscription-Key": self._api_key,
                    "Content-Type": "application/octet-stream",
                },
                method="POST",
            )
            with _open_url(request, timeout=self._timeout_seconds) as response:
                operation_location = (
                    response.headers.get("Operation-Location")
                    or response.headers.get("operation-location")
                )
            if not operation_location:
                raise OcrProviderError("Azure Vision OCR did not return an Operation-Location header.")

            result_payload = self._poll_azure_result(operation_location)
            recognized_lines = _extract_azure_lines(result_payload)
        except OcrProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - network/provider failures should be recoverable
            raise OcrProviderError("Azure Vision OCR request failed.") from exc

        if len(recognized_lines) == 0:
            return _build_fallback_lines(source_language=source_language, regions=regions)
        return _group_recognized_lines_to_regions(
            source_language=source_language,
            regions=regions,
            recognized_lines=recognized_lines,
        )

    def _poll_azure_result(self, operation_location: str) -> dict[str, object]:
        deadline = monotonic() + self._timeout_seconds
        while True:
            request = Request(
                operation_location,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                method="GET",
            )
            with _open_url(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))

            status = str(payload.get("status") or "").lower()
            if status == "succeeded":
                return payload
            if status == "failed":
                raise OcrProviderError("Azure Vision OCR returned a failed status.")
            if monotonic() >= deadline:
                raise OcrProviderError("Azure Vision OCR polling timed out.")
            sleep(self._poll_interval_seconds)


def _build_fallback_lines(
    *,
    source_language: str,
    regions: list[OcrCandidateRegion],
) -> list[OcrLine]:
    template = OCR_FALLBACK_TEMPLATES.get(source_language.split("-", 1)[0].lower(), "Text line {index}")
    ordered_regions = sorted(regions, key=lambda candidate: (candidate.y, candidate.x, candidate.id))
    return [
        OcrLine(
            region_id=region.id,
            text=template.format(index=index),
            confidence=round(region.confidence if region.confidence is not None else 0.68, 2),
        )
        for index, region in enumerate(ordered_regions, start=1)
    ]


def _group_recognized_lines_to_regions(
    *,
    source_language: str,
    regions: list[OcrCandidateRegion],
    recognized_lines: list[RecognizedLine],
) -> list[OcrLine]:
    ordered_regions = sorted(regions, key=lambda candidate: (candidate.y, candidate.x, candidate.id))
    grouped_lines: dict[str, list[RecognizedLine]] = {region.id: [] for region in ordered_regions}
    for recognized_line in sorted(recognized_lines, key=lambda line: (line.y, line.x, line.text)):
        target_region = _find_best_region_for_line(ordered_regions, recognized_line)
        grouped_lines[target_region.id].append(recognized_line)

    fallback_lines = _build_fallback_lines(source_language=source_language, regions=ordered_regions)
    fallback_lookup = {line.region_id: line for line in fallback_lines}
    extracted_lines: list[OcrLine] = []
    for region in ordered_regions:
        region_lines = grouped_lines[region.id]
        if len(region_lines) == 0:
            extracted_lines.append(fallback_lookup[region.id])
            continue
        text = "\n".join(line.text for line in region_lines if line.text.strip() != "").strip()
        if text == "":
            extracted_lines.append(fallback_lookup[region.id])
            continue
        average_confidence = sum(line.confidence for line in region_lines) / len(region_lines)
        extracted_lines.append(
            OcrLine(
                region_id=region.id,
                text=text,
                confidence=round(average_confidence, 2),
            )
        )
    return extracted_lines


def _find_best_region_for_line(
    regions: list[OcrCandidateRegion],
    recognized_line: RecognizedLine,
) -> OcrCandidateRegion:
    containing_region = next(
        (
            region
            for region in regions
            if region.x <= recognized_line.x <= region.x + region.width
            and region.y <= recognized_line.y <= region.y + region.height
        ),
        None,
    )
    if containing_region is not None:
        return containing_region

    return min(
        regions,
        key=lambda region: (
            (recognized_line.x - (region.x + region.width / 2)) ** 2
            + (recognized_line.y - (region.y + region.height / 2)) ** 2
        ),
    )


def _flatten_paddle_predict_output(raw_result: object) -> list[RecognizedLine]:
    recognized_lines: list[RecognizedLine] = []
    if not isinstance(raw_result, list):
        return recognized_lines

    for page_result in raw_result:
        if hasattr(page_result, "res"):
            page_payload = getattr(page_result, "res")
        elif isinstance(page_result, dict):
            page_payload = page_result.get("res", page_result)
        else:
            page_payload = None

        if not isinstance(page_payload, dict):
            continue

        rec_texts = page_payload.get("rec_texts")
        rec_scores = page_payload.get("rec_scores")
        rec_polys = page_payload.get("rec_polys") or page_payload.get("dt_polys")
        if not isinstance(rec_texts, list) or not isinstance(rec_polys, list):
            continue

        normalized_scores = (
            list(rec_scores)
            if isinstance(rec_scores, (list, tuple))
            else [1.0] * len(rec_texts)
        )
        for index, text_value in enumerate(rec_texts):
            text = str(text_value).strip()
            if text == "":
                continue
            polygon = rec_polys[index] if index < len(rec_polys) else None
            score = float(normalized_scores[index]) if index < len(normalized_scores) else 1.0
            center_x, center_y = _get_polygon_center(polygon)
            recognized_lines.append(
                RecognizedLine(
                    text=text,
                    confidence=score,
                    x=center_x,
                    y=center_y,
                )
            )
    return recognized_lines


def _flatten_paddle_legacy_output(raw_result: object) -> list[RecognizedLine]:
    recognized_lines: list[RecognizedLine] = []
    if not isinstance(raw_result, list):
        return recognized_lines

    for page_result in raw_result:
        if not isinstance(page_result, list):
            continue
        for line_result in page_result:
            if not isinstance(line_result, (list, tuple)) or len(line_result) < 2:
                continue
            polygon = line_result[0]
            text_info = line_result[1]
            if not isinstance(polygon, (list, tuple)) or not isinstance(text_info, (list, tuple)):
                continue
            if len(text_info) < 2:
                continue
            text = str(text_info[0]).strip()
            if text == "":
                continue
            score = float(text_info[1])
            center_x, center_y = _get_polygon_center(polygon)
            recognized_lines.append(
                RecognizedLine(
                    text=text,
                    confidence=score,
                    x=center_x,
                    y=center_y,
                )
            )
    return recognized_lines


def _extract_azure_lines(payload: dict[str, object]) -> list[RecognizedLine]:
    analyze_result = payload.get("analyzeResult")
    if not isinstance(analyze_result, dict):
        return []

    pages = analyze_result.get("pages")
    if isinstance(pages, list):
        recognized_lines = _extract_azure_page_lines(pages, polygon_key="polygon")
        if len(recognized_lines) > 0:
            return recognized_lines

    read_results = analyze_result.get("readResults")
    if isinstance(read_results, list):
        return _extract_azure_page_lines(read_results, polygon_key="boundingBox")

    return []


def _extract_azure_page_lines(
    page_entries: list[object],
    *,
    polygon_key: str,
) -> list[RecognizedLine]:
    recognized_lines: list[RecognizedLine] = []
    for page_entry in page_entries:
        if not isinstance(page_entry, dict):
            continue
        lines = page_entry.get("lines")
        if not isinstance(lines, list):
            continue
        for line in lines:
            if not isinstance(line, dict):
                continue
            text = str(line.get("text") or "").strip()
            polygon = line.get(polygon_key)
            if text == "" or not isinstance(polygon, list):
                continue
            center_x, center_y = _get_polygon_center(polygon)
            recognized_lines.append(
                RecognizedLine(
                    text=text,
                    confidence=0.9,
                    x=center_x,
                    y=center_y,
                )
            )
    return recognized_lines


def _get_polygon_center(polygon: object) -> tuple[float, float]:
    points = list(_iterate_polygon_points(polygon))
    if len(points) == 0:
        return 0.0, 0.0
    x_total = sum(point[0] for point in points)
    y_total = sum(point[1] for point in points)
    return x_total / len(points), y_total / len(points)


def _iterate_polygon_points(polygon: object):
    if not isinstance(polygon, (list, tuple)):
        return
    if len(polygon) == 0:
        return

    if all(isinstance(value, (int, float)) for value in polygon):
        numeric_values = [float(value) for value in polygon]
        for index in range(0, len(numeric_values), 2):
            if index + 1 >= len(numeric_values):
                break
            yield numeric_values[index], numeric_values[index + 1]
        return

    for point in polygon:
        if isinstance(point, dict):
            if "x" in point and "y" in point:
                yield float(point["x"]), float(point["y"])
            continue
        if (
            isinstance(point, (list, tuple))
            and len(point) >= 2
            and isinstance(point[0], (int, float))
            and isinstance(point[1], (int, float))
        ):
            yield float(point[0]), float(point[1])


def _map_source_language_to_paddle(source_language: str) -> str:
    language_code = source_language.split("-", 1)[0].lower()
    return {
        "ja": "japan",
        "ko": "korean",
        "zh": "ch",
        "en": "en",
    }.get(language_code, "en")
