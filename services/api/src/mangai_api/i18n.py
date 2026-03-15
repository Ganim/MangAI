from __future__ import annotations

import re

from mangai_api.constants import SUPPORTED_TEXT_DIRECTIONS, SUPPORTED_UI_LOCALES


LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
RTL_PRIMARY_LANGUAGES = {"ar", "fa", "he", "ur"}


class LocaleValidationError(ValueError):
    """Raised when locale or language normalization fails."""


def normalize_language_tag(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise LocaleValidationError("Language tag cannot be empty.")
    if not LANGUAGE_TAG_RE.fullmatch(raw):
        raise LocaleValidationError("Invalid BCP 47-like language tag.")

    segments = raw.split("-")
    primary = segments[0].lower()
    normalized_segments = [primary]

    for segment in segments[1:]:
        if len(segment) == 2 and segment.isalpha():
            normalized_segments.append(segment.upper())
        else:
            normalized_segments.append(segment)

    return "-".join(normalized_segments)


def normalize_ui_locale(value: str) -> str:
    normalized = normalize_language_tag(value)
    if normalized not in SUPPORTED_UI_LOCALES:
        raise LocaleValidationError(
            f"Unsupported UI locale. Expected one of: {', '.join(SUPPORTED_UI_LOCALES)}."
        )
    return normalized


def infer_text_direction(language_tag: str) -> str:
    normalized = normalize_language_tag(language_tag)
    primary_language = normalized.split("-")[0]
    direction = "rtl" if primary_language in RTL_PRIMARY_LANGUAGES else "ltr"
    if direction not in SUPPORTED_TEXT_DIRECTIONS:
        raise LocaleValidationError("Unsupported inferred text direction.")
    return direction
