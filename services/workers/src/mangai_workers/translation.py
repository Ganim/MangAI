from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationCandidate:
    dialogue_id: str
    content: str
    reading_order: int


@dataclass(frozen=True)
class TranslationOutput:
    dialogue_id: str
    content: str


TRANSLATION_TEMPLATES = {
    "pt": "Linha {index}",
    "en": "Line {index}",
}


def translate_dialogues(
    *,
    target_language: str,
    dialogues: list[TranslationCandidate],
) -> list[TranslationOutput]:
    template = TRANSLATION_TEMPLATES.get(target_language.split("-", 1)[0].lower(), "Line {index}")
    ordered_dialogues = sorted(dialogues, key=lambda candidate: (candidate.reading_order, candidate.dialogue_id))

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
