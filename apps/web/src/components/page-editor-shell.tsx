"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AppMessages } from "../i18n/index.ts";
import type { SupportedUiLocale } from "../i18n/config.ts";
import { ApiClientError, getProjectDetail, resolveApiAssetUrl } from "../features/projects/api.ts";
import {
  buildProjectPageEditorHref,
  buildProjectWorkspaceHref,
} from "../features/projects/routing.ts";
import { WorkspaceHeader } from "./workspace-header.tsx";

type PageEditorShellProps = {
  locale: SupportedUiLocale;
  messages: AppMessages;
  projectId: string;
  pageId: string;
};

type ProjectDetail = Awaited<ReturnType<typeof getProjectDetail>>;
type ProjectPage = ProjectDetail["pages"][number];

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}

export function PageEditorShell({
  locale,
  messages,
  projectId,
  pageId,
}: PageEditorShellProps) {
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let canceled = false;

    async function loadProject() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const response = await getProjectDetail(projectId);
        if (canceled) {
          return;
        }
        setProjectDetail(response);
      } catch (error) {
        if (canceled) {
          return;
        }
        setLoadError(getErrorMessage(error, messages.editor.loadErrorFallback));
      } finally {
        if (!canceled) {
          setIsLoading(false);
        }
      }
    }

    void loadProject();
    return () => {
      canceled = true;
    };
  }, [messages.editor.loadErrorFallback, projectId]);

  const pages = projectDetail?.pages ?? [];
  const currentPage = pages.find((candidate) => candidate.id === pageId) ?? null;

  return (
    <main className="page-shell editor-page-shell">
      <WorkspaceHeader
        backHref={buildProjectWorkspaceHref(locale, projectId)}
        backLabel={messages.editor.backToProject}
        locale={locale}
        messages={messages}
      />

      {loadError ? <p className="notice notice-error">{loadError}</p> : null}

      {isLoading ? (
        <section className="section-panel">
          <p className="empty-state">{messages.editor.loadingEditor}</p>
        </section>
      ) : currentPage ? (
        <section className="editor-layout">
          <aside className="section-panel editor-sidebar">
            <div className="section-head">
              <h2 className="section-title">{messages.editor.pageNavigatorTitle}</h2>
              <p className="section-copy">{messages.editor.pageNavigatorCopy}</p>
            </div>

            <div className="editor-page-list">
              {pages.map((page) => {
                const isCurrent = page.id === currentPage.id;
                return (
                  <Link
                    key={page.id}
                    className={isCurrent ? "editor-page-link editor-page-link-active" : "editor-page-link"}
                    href={buildProjectPageEditorHref(locale, projectId, page.id)}
                  >
                    <span className="card-step">
                      {messages.editor.pageLabel.replace("{index}", String(page.index))}
                    </span>
                    <strong>{page.file_name}</strong>
                  </Link>
                );
              })}
            </div>

            <div className="section-head section-head-compact">
              <h2 className="section-title">{messages.editor.sidebarTitle}</h2>
              <p className="section-copy">{messages.editor.sidebarCopy}</p>
            </div>

            <div className="status-list">
              {messages.editor.sidebarItems.map((item) => (
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

          <section className="section-panel editor-canvas-panel">
            <div className="editor-toolbar">
              <div>
                <span className="eyebrow">{messages.editor.kicker}</span>
                <h1 className="workspace-title editor-title">{currentPage.file_name}</h1>
                <p className="section-copy">{messages.editor.canvasCopy}</p>
              </div>
              <div className="editor-toolbar-actions">
                <button className="secondary-button" type="button">
                  {messages.editor.toggleMasksAction}
                </button>
                <button className="primary-button" type="button">
                  {messages.editor.openInspectorAction}
                </button>
              </div>
            </div>

            <div className="editor-canvas-frame">
              <img
                alt={currentPage.file_name}
                className="editor-page-image"
                src={resolveApiAssetUrl(currentPage.original_asset_path)}
              />
              <div className="editor-overlay editor-overlay-detection">
                <span>{messages.editor.overlayDetectedRegions}</span>
              </div>
              <div className="editor-overlay editor-overlay-text">
                <span>{messages.editor.overlayDialogueBlocks}</span>
              </div>
            </div>
          </section>
        </section>
      ) : (
        <section className="section-panel">
          <p className="empty-state">{messages.editor.pageNotFound}</p>
        </section>
      )}
    </main>
  );
}
