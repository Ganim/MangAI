import { normalizeUiLocale } from "@mangai/shared";

import { DEFAULT_UI_LOCALE, type SupportedUiLocale } from "./config.ts";

export function resolveUiLocale(value: string | undefined): SupportedUiLocale | null {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  try {
    return normalizeUiLocale(value);
  } catch {
    return null;
  }
}

export function getDefaultLocalePath(): `/${SupportedUiLocale}` {
  return `/${DEFAULT_UI_LOCALE}`;
}
