import Link from "next/link";

import type { AppMessages } from "../i18n/index.ts";
import { SUPPORTED_UI_LOCALE_LABELS, type SupportedUiLocale } from "../i18n/config.ts";

type WorkspaceHeaderProps = {
  locale: SupportedUiLocale;
  messages: AppMessages;
  backHref?: string;
  backLabel?: string;
};

export function WorkspaceHeader({
  locale,
  messages,
  backHref,
  backLabel,
}: WorkspaceHeaderProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">{messages.common.appName}</span>
        <span className="brand-note">{messages.common.brandNote}</span>
        {backHref && backLabel ? (
          <Link className="workspace-back-link" href={backHref}>
            {backLabel}
          </Link>
        ) : null}
      </div>

      <nav aria-label={messages.common.localeSwitcherLabel} className="locale-nav">
        {Object.entries(SUPPORTED_UI_LOCALE_LABELS).map(([candidateLocale, label]) => {
          const href = `/${candidateLocale}`;
          const isActive = candidateLocale === locale;
          const className = isActive ? "locale-link locale-link-active" : "locale-link";

          return (
            <Link
              key={candidateLocale}
              className={className}
              href={href}
              hrefLang={candidateLocale}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
