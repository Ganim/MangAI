import Link from "next/link";

import { DEFAULT_UI_LOCALE } from "../i18n/config.ts";

export default function NotFoundPage() {
  return (
    <main className="not-found-shell">
      <div className="not-found-card">
        <span className="eyebrow">MangAI</span>
        <h1>Page not found</h1>
        <p>The page or locale you requested is not available in this build yet.</p>
        <Link className="primary-button" href={`/${DEFAULT_UI_LOCALE}`}>
          Return to workspace
        </Link>
      </div>
    </main>
  );
}
