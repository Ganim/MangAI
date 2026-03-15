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

type ProjectWorkspaceProps = {
  locale: SupportedUiLocale;
  messages: AppMessages;
  projectId: string;
};

type ProjectDetail = Awaited<ReturnType<typeof getProjectDetail>>;

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}

export function ProjectWorkspace({ locale, messages, projectId }: ProjectWorkspaceProps) {
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
        setLoadError(getErrorMessage(error, messages.workspace.loadErrorFallback));
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
  }, [messages.workspace.loadErrorFallback, projectId]);

  return (
    <main className="page-shell">
      <WorkspaceHeader
        backHref={`/${locale}`}
        backLabel={messages.workspace.backToDashboard}
        locale={locale}
        messages={messages}
      />

      <section className="workspace-grid">
        <article className="section-panel workspace-hero-panel">
          <span className="eyebrow">{messages.workspace.kicker}</span>
          <h1 className="workspace-title">
            {projectDetail?.project.name ?? messages.workspace.loadingProjectTitle}
          </h1>
          <p className="section-copy">{messages.workspace.heroCopy}</p>

          {loadError ? <p className="notice notice-error">{loadError}</p> : null}

          {isLoading ? (
            <p className="empty-state">{messages.workspace.loadingProject}</p>
          ) : projectDetail ? (
            <div className="workspace-stat-grid">
              <article className="workspace-stat-card">
                <span className="card-step">{messages.workspace.sourceLanguageLabel}</span>
                <strong>{projectDetail.project.source_language}</strong>
              </article>
              <article className="workspace-stat-card">
                <span className="card-step">{messages.workspace.targetLanguageLabel}</span>
                <strong>{projectDetail.project.target_language}</strong>
              </article>
              <article className="workspace-stat-card">
                <span className="card-step">{messages.workspace.pageCountLabel}</span>
                <strong>{String(projectDetail.project.page_count)}</strong>
              </article>
              <article className="workspace-stat-card">
                <span className="card-step">{messages.workspace.statusLabel}</span>
                <strong>{projectDetail.project.status}</strong>
              </article>
            </div>
          ) : null}
        </article>

        <article className="section-panel workspace-summary-panel">
          <div className="section-head">
            <h2 className="section-title">{messages.workspace.summaryTitle}</h2>
            <p className="section-copy">{messages.workspace.summaryCopy}</p>
          </div>

          <div className="status-list">
            {messages.workspace.summaryItems.map((item) => (
              <article className="status-item" key={item.label}>
                <div className="status-item-header">
                  <span className="status-item-label">{item.label}</span>
                  <span className="status-item-value">{item.value}</span>
                </div>
                <p className="card-description">{item.description}</p>
              </article>
            ))}
          </div>
        </article>

        <article className="section-panel workspace-span-2">
          <div className="section-head">
            <h2 className="section-title">{messages.workspace.pagesTitle}</h2>
            <p className="section-copy">{messages.workspace.pagesCopy}</p>
          </div>

          {isLoading ? (
            <p className="empty-state">{messages.workspace.loadingProject}</p>
          ) : projectDetail?.pages.length ? (
            <div className="workspace-page-grid">
              {projectDetail.pages.map((page) => (
                <article className="stored-page-card" key={page.id}>
                  <div className="stored-page-preview-frame">
                    <img
                      alt={page.file_name}
                      className="stored-page-preview"
                      src={resolveApiAssetUrl(page.original_asset_path)}
                    />
                  </div>
                  <div className="stored-page-body">
                    <span className="card-step">
                      {messages.workspace.pageLabel.replace("{index}", String(page.index))}
                    </span>
                    <h3 className="card-title">{page.file_name}</h3>
                    <p className="card-description">
                      {page.mime_type} · {page.width ?? "?"} x {page.height ?? "?"}
                    </p>
                    <div className="workspace-page-actions">
                      <Link
                        className="secondary-button"
                        href={buildProjectWorkspaceHref(locale, projectId)}
                      >
                        {messages.workspace.stayInProjectAction}
                      </Link>
                      <Link
                        className="primary-button"
                        href={buildProjectPageEditorHref(locale, projectId, page.id)}
                      >
                        {messages.workspace.openEditorAction}
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-state">{messages.workspace.emptyPages}</p>
          )}
        </article>
      </section>
    </main>
  );
}
