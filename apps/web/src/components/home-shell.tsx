import Link from "next/link";

import type { AppMessages } from "../i18n/index.ts";
import {
  DEFAULT_UI_LOCALE,
  SUPPORTED_UI_LOCALE_LABELS,
  type SupportedUiLocale,
} from "../i18n/config.ts";

type HomeShellProps = {
  locale: SupportedUiLocale;
  messages: AppMessages;
};

export function HomeShell({ locale, messages }: HomeShellProps) {
  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">{messages.common.appName}</span>
          <span className="brand-note">{messages.common.brandNote}</span>
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
                locale={false}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </header>

      <section className="hero">
        <article className="hero-panel">
          <span className="eyebrow">{messages.home.eyebrow}</span>
          <h1 className="hero-title">{messages.home.title}</h1>
          <p className="hero-subtitle">{messages.home.subtitle}</p>

          <div className="hero-actions">
            <Link className="primary-button" href={`/${locale}#workflow`} locale={false}>
              {messages.home.primaryAction}
            </Link>
            <Link className="secondary-button" href={`/${locale}#foundation`} locale={false}>
              {messages.home.secondaryAction}
            </Link>
          </div>
        </article>

        <aside className="status-panel" id="foundation">
          <div className="section-head">
            <h2 className="status-title">{messages.home.foundationTitle}</h2>
            <p className="status-copy">{messages.home.foundationCopy}</p>
          </div>

          <div className="status-list">
            {messages.home.foundationItems.map((item) => (
              <article className="status-item" key={item.label}>
                <div className="status-item-header">
                  <span className="status-item-label">{item.label}</span>
                  <span className="status-item-value">{item.value}</span>
                </div>
                <p className="card-description">{item.description}</p>
              </article>
            ))}
          </div>
        </aside>
      </section>

      <section className="section-panel" id="workflow">
        <div className="section-head">
          <h2 className="section-title">{messages.home.workflowTitle}</h2>
          <p className="section-copy">{messages.home.workflowCopy}</p>
        </div>

        <div className="card-grid">
          {messages.home.workflowItems.map((item) => (
            <article className="card" key={item.step}>
              <span className="card-step">{item.step}</span>
              <h3 className="card-title">{item.title}</h3>
              <p className="card-description">{item.description}</p>
            </article>
          ))}
        </div>

        <p className="milestone-note">{messages.home.milestoneNote}</p>
      </section>

      <section className="section-panel">
        <div className="section-head">
          <h2 className="section-title">{messages.home.deliveryTitle}</h2>
          <p className="section-copy">{messages.home.deliveryCopy}</p>
        </div>

        <div className="card-grid">
          {messages.home.deliveryItems.map((item) => (
            <article className="card" key={item.step}>
              <span className="card-step">{item.step}</span>
              <h3 className="card-title">{item.title}</h3>
              <p className="card-description">{item.description}</p>
            </article>
          ))}
        </div>

        <p className="milestone-note">
          {messages.home.defaultWorkspaceLabel}: <strong>{DEFAULT_UI_LOCALE}</strong>
        </p>
      </section>
    </main>
  );
}
