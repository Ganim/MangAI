"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AppMessages } from "../i18n/index.ts";
import type { SupportedUiLocale } from "../i18n/config.ts";
import {
  ApiClientError,
  createPageRegion,
  getPageRegions,
  getProjectDetail,
  resolveApiAssetUrl,
  updatePageRegion,
} from "../features/projects/api.ts";
import {
  buildDefaultRegionInput,
  formatRegionBounds,
  formatRegionIndexLabel,
  getPageCanvasSize,
  getRegionOverlayStyle,
} from "../features/projects/regions.ts";
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
type PageRegionsResponse = Awaited<ReturnType<typeof getPageRegions>>;
type PageRegion = PageRegionsResponse["regions"][number];

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}

function getRegionCardClassName(region: PageRegion, isSelected: boolean) {
  const baseClass = `editor-region-card editor-region-card-${region.state}`;
  return isSelected ? `${baseClass} editor-region-card-selected` : baseClass;
}

function getRegionOverlayClassName(region: PageRegion, isSelected: boolean) {
  const baseClass = `editor-region-overlay editor-region-overlay-${region.state}`;
  return isSelected ? `${baseClass} editor-region-overlay-selected` : baseClass;
}

export function PageEditorShell({
  locale,
  messages,
  projectId,
  pageId,
}: PageEditorShellProps) {
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [regions, setRegions] = useState<PageRegion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegionsLoading, setIsRegionsLoading] = useState(false);
  const [isCreatingRegion, setIsCreatingRegion] = useState(false);
  const [updatingRegionId, setUpdatingRegionId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [regionLoadError, setRegionLoadError] = useState<string | null>(null);
  const [regionActionError, setRegionActionError] = useState<string | null>(null);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
  const [showRegions, setShowRegions] = useState(true);

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

  useEffect(() => {
    if (currentPage === null) {
      setRegions([]);
      setSelectedRegionId(null);
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function loadRegions() {
      setIsRegionsLoading(true);
      setRegionLoadError(null);
      try {
        const response = await getPageRegions(projectId, nextPage.id);
        if (canceled) {
          return;
        }
        setRegions(response.regions);
        setSelectedRegionId((currentSelectedRegionId) =>
          response.regions.some((region) => region.id === currentSelectedRegionId)
            ? currentSelectedRegionId
            : (response.regions[0]?.id ?? null),
        );
      } catch (error) {
        if (canceled) {
          return;
        }
        setRegionLoadError(getErrorMessage(error, messages.editor.regionLoadErrorFallback));
      } finally {
        if (!canceled) {
          setIsRegionsLoading(false);
        }
      }
    }

    void loadRegions();
    return () => {
      canceled = true;
    };
  }, [currentPage, messages.editor.regionLoadErrorFallback, projectId]);

  const selectedRegion =
    regions.find((candidate) => candidate.id === selectedRegionId) ?? null;
  const currentCanvasSize = currentPage
    ? getPageCanvasSize({ width: currentPage.width, height: currentPage.height })
    : null;

  async function handleCreateRegion() {
    if (currentPage === null) {
      return;
    }

    setIsCreatingRegion(true);
    setRegionActionError(null);

    try {
      const response = await createPageRegion(
        projectId,
        currentPage.id,
        buildDefaultRegionInput({
          width: currentPage.width,
          height: currentPage.height,
        }),
      );
      setRegions((currentRegions) => [...currentRegions, response.region]);
      setSelectedRegionId(response.region.id);
      setShowRegions(true);
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionCreateErrorFallback));
    } finally {
      setIsCreatingRegion(false);
    }
  }

  async function handleUpdateRegionState(nextState: PageRegion["state"]) {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    setUpdatingRegionId(selectedRegion.id);
    setRegionActionError(null);

    try {
      const response = await updatePageRegion(projectId, currentPage.id, selectedRegion.id, {
        state: nextState,
      });
      setRegions((currentRegions) =>
        currentRegions.map((region) =>
          region.id === response.region.id ? response.region : region,
        ),
      );
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionUpdateErrorFallback));
    } finally {
      setUpdatingRegionId(null);
    }
  }

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

            {regionLoadError ? <p className="notice notice-error">{regionLoadError}</p> : null}
            {regionActionError ? <p className="notice notice-error">{regionActionError}</p> : null}

            {isRegionsLoading ? (
              <p className="empty-state">{messages.editor.regionsLoading}</p>
            ) : regions.length === 0 ? (
              <p className="empty-state">{messages.editor.regionsEmpty}</p>
            ) : (
              <div className="editor-region-list">
                {regions.map((region, index) => {
                  const isSelected = region.id === selectedRegionId;
                  return (
                    <article className={getRegionCardClassName(region, isSelected)} key={region.id}>
                      <div className="editor-region-card-header">
                        <span className="card-step">{formatRegionIndexLabel(index)}</span>
                        <span className="editor-region-state-pill">
                          {messages.editor.regionStateLabels[region.state]}
                        </span>
                      </div>
                      <strong>{messages.editor.regionTypeLabels[region.type]}</strong>
                      <p className="card-description">{formatRegionBounds(region)}</p>
                      <button
                        className={isSelected ? "secondary-button" : "ghost-button"}
                        onClick={() => setSelectedRegionId(region.id)}
                        type="button"
                      >
                        {isSelected
                          ? messages.editor.selectedRegionAction
                          : messages.editor.selectRegionAction}
                      </button>
                    </article>
                  );
                })}
              </div>
            )}

            <div className="section-head section-head-compact">
              <h2 className="section-title">{messages.editor.selectionTitle}</h2>
              <p className="section-copy">{messages.editor.selectionCopy}</p>
            </div>

            {selectedRegion ? (
              <div className="editor-selection-panel">
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionTypeLabel}</span>
                  <strong>{messages.editor.regionTypeLabels[selectedRegion.type]}</strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionStateLabel}</span>
                  <strong>{messages.editor.regionStateLabels[selectedRegion.state]}</strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionOriginLabel}</span>
                  <strong>{messages.editor.regionOriginLabels[selectedRegion.origin]}</strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionBoundsLabel}</span>
                  <strong>{formatRegionBounds(selectedRegion)}</strong>
                </div>

                <div className="editor-selection-actions">
                  <button
                    className="ghost-button"
                    disabled={updatingRegionId === selectedRegion.id}
                    onClick={() => void handleUpdateRegionState("reviewed")}
                    type="button"
                  >
                    {messages.editor.markReviewedAction}
                  </button>
                  <button
                    className="secondary-button"
                    disabled={updatingRegionId === selectedRegion.id}
                    onClick={() => void handleUpdateRegionState("approved")}
                    type="button"
                  >
                    {messages.editor.approveRegionAction}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={updatingRegionId === selectedRegion.id}
                    onClick={() => void handleUpdateRegionState("draft")}
                    type="button"
                  >
                    {messages.editor.resetRegionAction}
                  </button>
                </div>
              </div>
            ) : (
              <p className="empty-state">{messages.editor.selectionEmpty}</p>
            )}
          </aside>

          <section className="section-panel editor-canvas-panel">
            <div className="editor-toolbar">
              <div>
                <span className="eyebrow">{messages.editor.kicker}</span>
                <h1 className="workspace-title editor-title">{currentPage.file_name}</h1>
                <p className="section-copy">{messages.editor.canvasCopy}</p>
              </div>
              <div className="editor-toolbar-actions">
                <button
                  className="secondary-button"
                  onClick={() => setShowRegions((currentValue) => !currentValue)}
                  type="button"
                >
                  {showRegions
                    ? messages.editor.hideRegionsAction
                    : messages.editor.showRegionsAction}
                </button>
                <button
                  className="primary-button"
                  disabled={isCreatingRegion}
                  onClick={() => void handleCreateRegion()}
                  type="button"
                >
                  {isCreatingRegion
                    ? messages.editor.creatingRegionAction
                    : messages.editor.addRegionAction}
                </button>
              </div>
            </div>

            {currentCanvasSize?.usedFallback ? (
              <p className="notice notice-warning">{messages.editor.dimensionsFallbackNotice}</p>
            ) : null}

            <div className="editor-canvas-frame">
              <div
                className="editor-page-stage"
                style={{
                  aspectRatio: `${currentCanvasSize?.width ?? 1000} / ${currentCanvasSize?.height ?? 1400}`,
                }}
              >
                <img
                  alt={currentPage.file_name}
                  className="editor-page-image"
                  src={resolveApiAssetUrl(currentPage.original_asset_path)}
                />

                <div className="editor-overlay editor-overlay-detection">
                  <span>
                    {messages.editor.overlayRegionCount.replace("{count}", String(regions.length))}
                  </span>
                </div>

                {regions.length === 0 ? (
                  <div className="editor-canvas-empty">
                    <span>{messages.editor.canvasEmptyState}</span>
                  </div>
                ) : null}

                {showRegions
                  ? regions.map((region, index) => {
                      const isSelected = region.id === selectedRegionId;
                      return (
                        <button
                          aria-pressed={isSelected}
                          className={getRegionOverlayClassName(region, isSelected)}
                          key={region.id}
                          onClick={() => setSelectedRegionId(region.id)}
                          style={getRegionOverlayStyle(region, currentPage)}
                          type="button"
                        >
                          <span className="editor-region-chip">{formatRegionIndexLabel(index)}</span>
                          <span className="editor-region-caption">
                            {messages.editor.regionTypeLabels[region.type]}
                          </span>
                        </button>
                      );
                    })
                  : null}
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
