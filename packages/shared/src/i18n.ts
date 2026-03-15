import { RTL_LANGUAGE_CODES, SUPPORTED_UI_LOCALES } from "./enums.ts";
import { ValidationError } from "./errors.ts";

export function canonicalizeLanguageTag(value: unknown, path: Array<string | number> = []): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new ValidationError("Expected a non-empty language tag", path);
  }

  try {
    return Intl.getCanonicalLocales(value.trim())[0]!;
  } catch {
    throw new ValidationError("Invalid BCP 47 language tag", path);
  }
}

export function normalizeUiLocale(
  value: unknown,
  path: Array<string | number> = [],
): (typeof SUPPORTED_UI_LOCALES)[number] {
  const locale = canonicalizeLanguageTag(value, path);
  if (!SUPPORTED_UI_LOCALES.includes(locale as (typeof SUPPORTED_UI_LOCALES)[number])) {
    throw new ValidationError(
      `Unsupported UI locale. Expected one of: ${SUPPORTED_UI_LOCALES.join(", ")}`,
      path,
    );
  }
  return locale as (typeof SUPPORTED_UI_LOCALES)[number];
}

export function inferTextDirectionForLanguage(languageTag: unknown): "ltr" | "rtl" {
  const normalized = canonicalizeLanguageTag(languageTag);
  const primaryLanguage = normalized.split("-")[0]!.toLowerCase();
  return RTL_LANGUAGE_CODES.includes(primaryLanguage as (typeof RTL_LANGUAGE_CODES)[number])
    ? "rtl"
    : "ltr";
}
