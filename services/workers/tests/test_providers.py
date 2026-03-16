import json

import pytest

from mangai_workers.config import WorkerSettings
from mangai_workers.ocr import OcrCandidateRegion, OcrProviderError, extract_ocr_lines_from_asset
from mangai_workers.translation import (
    TranslationCandidate,
    TranslationProviderError,
    translate_dialogues,
)


class FakeHttpResponse:
    def __init__(self, payload=None, *, headers=None) -> None:
        self._payload = payload
        self.headers = headers or {}

    def read(self) -> bytes:
        if self._payload is None:
            return b""
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_ocr_provider_falls_back_when_selected_provider_fails(monkeypatch, tmp_path) -> None:
    asset_path = tmp_path / "page.png"
    asset_path.write_bytes(b"fake-image")

    def raise_provider_error(*args, **kwargs):
        raise OcrProviderError("simulated provider failure")

    monkeypatch.setattr("mangai_workers.ocr.PaddleOcrProvider.extract", raise_provider_error)

    lines = extract_ocr_lines_from_asset(
        asset_path=asset_path,
        source_language="ja-JP",
        regions=[
            OcrCandidateRegion(
                id="region-1",
                type="speech_balloon",
                confidence=0.82,
                x=10,
                y=10,
                width=100,
                height=60,
            )
        ],
        settings=WorkerSettings(ocr_provider="paddleocr"),
    )

    assert len(lines) == 1
    assert lines[0].text == "テキスト 1"


def test_azure_vision_provider_extracts_and_groups_lines(monkeypatch, tmp_path) -> None:
    asset_path = tmp_path / "page.png"
    asset_path.write_bytes(b"fake-image")
    responses = iter(
        [
            FakeHttpResponse(headers={"Operation-Location": "https://example.com/operations/123"}),
            FakeHttpResponse(
                {
                    "status": "succeeded",
                    "analyzeResult": {
                        "pages": [
                            {
                                "lines": [
                                    {
                                        "text": "Detected line",
                                        "polygon": [10, 10, 110, 10, 110, 70, 10, 70],
                                    }
                                ]
                            }
                        ]
                    },
                }
            ),
        ]
    )

    monkeypatch.setattr("mangai_workers.ocr._open_url", lambda request, timeout=0: next(responses))

    lines = extract_ocr_lines_from_asset(
        asset_path=asset_path,
        source_language="en-US",
        regions=[
            OcrCandidateRegion(
                id="region-1",
                type="speech_balloon",
                confidence=0.82,
                x=10,
                y=10,
                width=100,
                height=60,
            )
        ],
        settings=WorkerSettings(
            ocr_provider="azure_vision",
            azure_vision_read_url="https://example.com/read",
            azure_vision_api_key="vision-key",
        ),
    )

    assert len(lines) == 1
    assert lines[0].region_id == "region-1"
    assert lines[0].text == "Detected line"


def test_azure_translation_provider_builds_request_and_returns_outputs(monkeypatch) -> None:
    captured_urls: list[str] = []

    def fake_open_url(request, timeout=0):
        captured_urls.append(request.full_url)
        return FakeHttpResponse(
            [
                {"translations": [{"text": "Linha traduzida 1"}]},
                {"translations": [{"text": "Linha traduzida 2"}]},
            ]
        )

    monkeypatch.setattr("mangai_workers.translation._open_url", fake_open_url)

    outputs = translate_dialogues(
        source_language="ja-JP",
        target_language="pt-BR",
        dialogues=[
            TranslationCandidate(dialogue_id="d1", content="テキスト 1", reading_order=1),
            TranslationCandidate(dialogue_id="d2", content="テキスト 2", reading_order=2),
        ],
        settings=WorkerSettings(
            translation_provider="azure_translator",
            azure_translator_api_key="translator-key",
            azure_translator_region="brazilsouth",
        ),
    )

    assert "api-version=3.0" in captured_urls[0]
    assert len(outputs) == 2
    assert outputs[0].content == "Linha traduzida 1"


def test_deepl_provider_builds_request_and_returns_outputs(monkeypatch) -> None:
    def fake_open_url(request, timeout=0):
        assert request.full_url == "https://api-free.deepl.com/v2/translate"
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["target_lang"] == "PT-BR"
        return FakeHttpResponse(
            {"translations": [{"text": "Linha 1"}, {"text": "Linha 2"}]}
        )

    monkeypatch.setattr("mangai_workers.translation._open_url", fake_open_url)

    outputs = translate_dialogues(
        source_language="ja-JP",
        target_language="pt-BR",
        dialogues=[
            TranslationCandidate(dialogue_id="d1", content="テキスト 1", reading_order=1),
            TranslationCandidate(dialogue_id="d2", content="テキスト 2", reading_order=2),
        ],
        settings=WorkerSettings(
            translation_provider="deepl",
            deepl_api_key="deepl-key",
        ),
    )

    assert len(outputs) == 2
    assert outputs[1].content == "Linha 2"


def test_translation_provider_falls_back_when_http_request_fails(monkeypatch) -> None:
    def raise_translation_error(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr("mangai_workers.translation._open_url", raise_translation_error)

    outputs = translate_dialogues(
        source_language="ja-JP",
        target_language="pt-BR",
        dialogues=[TranslationCandidate(dialogue_id="d1", content="テキスト 1", reading_order=1)],
        settings=WorkerSettings(
            translation_provider="azure_translator",
            azure_translator_api_key="translator-key",
        ),
    )

    assert len(outputs) == 1
    assert outputs[0].content.startswith("Linha 1")


def test_translation_provider_raises_in_strict_mode(monkeypatch) -> None:
    def raise_translation_error(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr("mangai_workers.translation._open_url", raise_translation_error)

    with pytest.raises(TranslationProviderError):
        translate_dialogues(
            source_language="ja-JP",
            target_language="pt-BR",
            dialogues=[TranslationCandidate(dialogue_id="d1", content="text", reading_order=1)],
            settings=WorkerSettings(
                translation_provider="azure_translator",
                azure_translator_api_key="translator-key",
                strict_provider_selection=True,
            ),
        )
