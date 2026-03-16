from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen


if TYPE_CHECKING:
    from mangai_workers.config import WorkerSettings


@dataclass(frozen=True)
class TranslationCandidate:
    dialogue_id: str
    content: str
    reading_order: int


@dataclass(frozen=True)
class TranslationOutput:
    dialogue_id: str
    content: str


class TranslationProviderError(Exception):
    pass


class TranslationProvider(Protocol):
    def translate(
        self,
        *,
        source_language: str,
        target_language: str,
        dialogues: list[TranslationCandidate],
    ) -> list[TranslationOutput]: ...


TRANSLATION_TEMPLATES = {
    "pt": "Linha {index}",
    "en": "Line {index}",
}

_open_url = urlopen


def translate_dialogues(
    *,
    source_language: str,
    target_language: str,
    dialogues: list[TranslationCandidate],
    settings: WorkerSettings,
) -> list[TranslationOutput]:
    provider = build_translation_provider(settings)
    try:
        return provider.translate(
            source_language=source_language,
            target_language=target_language,
            dialogues=dialogues,
        )
    except TranslationProviderError:
        if settings.strict_provider_selection:
            raise
        return FallbackTranslationProvider().translate(
            source_language=source_language,
            target_language=target_language,
            dialogues=dialogues,
        )


def build_translation_provider(settings: WorkerSettings) -> TranslationProvider:
    provider_name = settings.translation_provider
    try:
        if provider_name == "fallback":
            return FallbackTranslationProvider()
        if provider_name == "azure_translator":
            return AzureTranslatorProvider(settings)
        if provider_name == "deepl":
            return DeepLTranslationProvider(settings)
        raise TranslationProviderError(f"Unsupported translation provider '{provider_name}'.")
    except TranslationProviderError:
        if settings.strict_provider_selection:
            raise
        return FallbackTranslationProvider()


class FallbackTranslationProvider:
    def translate(
        self,
        *,
        source_language: str,
        target_language: str,
        dialogues: list[TranslationCandidate],
    ) -> list[TranslationOutput]:
        del source_language
        template = TRANSLATION_TEMPLATES.get(target_language.split("-", 1)[0].lower(), "Line {index}")
        ordered_dialogues = sorted(
            dialogues,
            key=lambda candidate: (candidate.reading_order, candidate.dialogue_id),
        )

        outputs: list[TranslationOutput] = []
        for index, dialogue in enumerate(ordered_dialogues, start=1):
            normalized_content = dialogue.content.strip()
            translated_content = (
                template.format(index=index)
                if normalized_content == ""
                else f"{template.format(index=index)}: {normalized_content}"
            )
            outputs.append(
                TranslationOutput(
                    dialogue_id=dialogue.dialogue_id,
                    content=translated_content,
                )
            )
        return outputs


class AzureTranslatorProvider:
    def __init__(self, settings: WorkerSettings) -> None:
        self._endpoint = settings.azure_translator_endpoint.rstrip("/")
        self._api_key = settings.azure_translator_api_key
        self._region = settings.azure_translator_region
        self._timeout_seconds = settings.http_timeout_seconds
        if self._api_key is None:
            raise TranslationProviderError(
                "Azure Translator requires MANGAI_AZURE_TRANSLATOR_API_KEY."
            )

    def translate(
        self,
        *,
        source_language: str,
        target_language: str,
        dialogues: list[TranslationCandidate],
    ) -> list[TranslationOutput]:
        ordered_dialogues = sorted(
            dialogues,
            key=lambda candidate: (candidate.reading_order, candidate.dialogue_id),
        )
        request_payload = [{"text": dialogue.content} for dialogue in ordered_dialogues]
        query = urlencode(
            {
                "api-version": "3.0",
                "from": source_language,
                "to": target_language,
            }
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/json; charset=UTF-8",
        }
        if self._region is not None:
            headers["Ocp-Apim-Subscription-Region"] = self._region

        try:
            request = Request(
                f"{self._endpoint}/translate?{query}",
                data=json.dumps(request_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with _open_url(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - network/provider failures should be recoverable
            raise TranslationProviderError("Azure Translator request failed.") from exc

        if not isinstance(payload, list):
            raise TranslationProviderError("Azure Translator returned an unexpected payload.")

        outputs: list[TranslationOutput] = []
        for dialogue, item in zip(ordered_dialogues, payload, strict=False):
            if not isinstance(item, dict):
                continue
            translations = item.get("translations")
            if not isinstance(translations, list) or len(translations) == 0:
                continue
            first_translation = translations[0]
            if not isinstance(first_translation, dict):
                continue
            text = str(first_translation.get("text") or "").strip()
            if text == "":
                continue
            outputs.append(TranslationOutput(dialogue_id=dialogue.dialogue_id, content=text))

        if len(outputs) == 0:
            raise TranslationProviderError("Azure Translator returned no translated text.")
        return outputs


class DeepLTranslationProvider:
    def __init__(self, settings: WorkerSettings) -> None:
        self._api_key = settings.deepl_api_key
        self._base_url = settings.deepl_api_base_url.rstrip("/")
        self._timeout_seconds = settings.http_timeout_seconds
        if self._api_key is None:
            raise TranslationProviderError("DeepL requires MANGAI_DEEPL_API_KEY.")

    def translate(
        self,
        *,
        source_language: str,
        target_language: str,
        dialogues: list[TranslationCandidate],
    ) -> list[TranslationOutput]:
        ordered_dialogues = sorted(
            dialogues,
            key=lambda candidate: (candidate.reading_order, candidate.dialogue_id),
        )
        try:
            request = Request(
                f"{self._base_url}/translate",
                data=json.dumps(
                    {
                        "text": [dialogue.content for dialogue in ordered_dialogues],
                        "source_lang": _map_language_to_deepl(source_language, source=True),
                        "target_lang": _map_language_to_deepl(target_language, source=False),
                    }
                ).encode("utf-8"),
                headers={
                    "Authorization": f"DeepL-Auth-Key {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with _open_url(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TranslationProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - network/provider failures should be recoverable
            raise TranslationProviderError("DeepL request failed.") from exc

        translations = payload.get("translations")
        if not isinstance(translations, list):
            raise TranslationProviderError("DeepL returned an unexpected payload.")

        outputs: list[TranslationOutput] = []
        for dialogue, item in zip(ordered_dialogues, translations, strict=False):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text == "":
                continue
            outputs.append(TranslationOutput(dialogue_id=dialogue.dialogue_id, content=text))

        if len(outputs) == 0:
            raise TranslationProviderError("DeepL returned no translated text.")
        return outputs


def _map_language_to_deepl(language: str, *, source: bool) -> str:
    normalized_language = language.replace("_", "-").upper()
    direct_mapping = {
        "EN": "EN",
        "EN-US": "EN-US" if not source else "EN",
        "PT": "PT",
        "PT-BR": "PT-BR" if not source else "PT",
        "JA": "JA",
        "JA-JP": "JA",
        "KO": "KO",
        "KO-KR": "KO",
        "ZH": "ZH",
        "ZH-CN": "ZH",
        "ZH-HANS": "ZH",
        "ZH-TW": "ZH",
        "ZH-HANT": "ZH",
    }
    if normalized_language in direct_mapping:
        return direct_mapping[normalized_language]
    base_language = normalized_language.split("-", 1)[0]
    if base_language in direct_mapping:
        return direct_mapping[base_language]
    raise TranslationProviderError(
        f"DeepL does not support the configured language '{language}'."
    )
