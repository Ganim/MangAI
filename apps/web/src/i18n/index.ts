import { normalizeUiLocale } from "@mangai/shared";

import type { SupportedUiLocale } from "./config.ts";
import { enUSMessages, type AppMessages } from "./messages/en-US.ts";
import { ptBRMessages } from "./messages/pt-BR.ts";

const MESSAGE_CATALOG: Record<SupportedUiLocale, AppMessages> = {
  "en-US": enUSMessages,
  "pt-BR": ptBRMessages,
};

export type { AppMessages };

export function getMessages(locale: SupportedUiLocale | string): AppMessages {
  return MESSAGE_CATALOG[normalizeUiLocale(locale)];
}
