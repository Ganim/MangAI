import { SUPPORTED_UI_LOCALES } from "@mangai/shared";

export type SupportedUiLocale = (typeof SUPPORTED_UI_LOCALES)[number];

export const DEFAULT_UI_LOCALE: SupportedUiLocale = "en-US";

export const SUPPORTED_UI_LOCALE_LABELS: Record<SupportedUiLocale, string> = {
  "en-US": "English",
  "pt-BR": "Português (Brasil)",
};
