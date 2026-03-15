import { normalizeUiLocale } from "@mangai/shared";

import { enUSMessages } from "./messages/en-US.ts";
import { ptBRMessages } from "./messages/pt-BR.ts";

const MESSAGE_CATALOG = {
  "en-US": enUSMessages,
  "pt-BR": ptBRMessages,
} as const;

export function getMessages(locale: string) {
  return MESSAGE_CATALOG[normalizeUiLocale(locale)];
}
