"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { AppMessages } from "../i18n/index.ts";
import type { SupportedUiLocale } from "../i18n/config.ts";
import {
  ApiClientError,
  createMaskRevision,
  createPageJob,
  createPageRegion,
  getPageJobs,
  getPageMaskRevisions,
  getPageRegions,
  getProjectDetail,
  resolveApiAssetUrl,
  updateMaskRevision,
  updatePageRegion,
} from "../features/projects/api.ts";
import {
  hasPendingPageJobs,
} from "../features/projects/jobs.ts";
import {
  buildMaskRevisionInputFromRegion,
  countApprovedActiveMaskRevisions,
  getActiveMaskRevisionForRegion,
  hasApprovedActiveMaskRevisions,
} from "../features/projects/masks.ts";
import {
  buildDefaultRegionInput,
  formatRegionBounds,
  formatRegionIndexLabel,
  getBoundingBoxAdjustmentStep,
  getPageCanvasSize,
  getRegionOverlayStyle,
  moveBoundingBox,
  resizeBoundingBox,
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
type PageJobsResponse = Awaited<ReturnType<typeof getPageJobs>>;
type PageJob = PageJobsResponse["jobs"][number];
type PageMaskRevisionsResponse = Awaited<ReturnType<typeof getPageMaskRevisions>>;
type PageMaskRevision = PageMaskRevisionsResponse["mask_revisions"][number];

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
  const [jobs, setJobs] = useState<PageJob[]>([]);
  const [maskRevisions, setMaskRevisions] = useState<PageMaskRevision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegionsLoading, setIsRegionsLoading] = useState(false);
  const [isMaskRevisionsLoading, setIsMaskRevisionsLoading] = useState(false);
  const [isCreatingRegion, setIsCreatingRegion] = useState(false);
  const [isJobsLoading, setIsJobsLoading] = useState(false);
  const [isQueueingDetection, setIsQueueingDetection] = useState(false);
  const [isQueueingCleanup, setIsQueueingCleanup] = useState(false);
  const [isCreatingMaskRevision, setIsCreatingMaskRevision] = useState(false);
  const [updatingRegionId, setUpdatingRegionId] = useState<string | null>(null);
  const [updatingMaskRevisionId, setUpdatingMaskRevisionId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [regionLoadError, setRegionLoadError] = useState<string | null>(null);
  const [regionActionError, setRegionActionError] = useState<string | null>(null);
  const [jobLoadError, setJobLoadError] = useState<string | null>(null);
  const [jobActionError, setJobActionError] = useState<string | null>(null);
  const [maskLoadError, setMaskLoadError] = useState<string | null>(null);
  const [maskActionError, setMaskActionError] = useState<string | null>(null);
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

  async function refreshProjectDetailState() {
    const response = await getProjectDetail(projectId);
    setProjectDetail(response);
    return response;
  }

  useEffect(() => {
    if (currentPage === null) {
      setRegions([]);
      setJobs([]);
      setMaskRevisions([]);
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

  useEffect(() => {
    if (currentPage === null) {
      setJobs([]);
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function loadJobs() {
      setIsJobsLoading(true);
      setJobLoadError(null);
      try {
        const response = await getPageJobs(projectId, nextPage.id);
        if (canceled) {
          return;
        }
        setJobs(response.jobs);
      } catch (error) {
        if (canceled) {
          return;
        }
        setJobLoadError(getErrorMessage(error, messages.editor.jobLoadErrorFallback));
      } finally {
        if (!canceled) {
          setIsJobsLoading(false);
        }
      }
    }

    void loadJobs();
    return () => {
      canceled = true;
    };
  }, [currentPage, messages.editor.jobLoadErrorFallback, projectId]);

  useEffect(() => {
    if (currentPage === null) {
      setMaskRevisions([]);
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function loadMaskRevisions() {
      setIsMaskRevisionsLoading(true);
      setMaskLoadError(null);
      try {
        const response = await getPageMaskRevisions(projectId, nextPage.id);
        if (canceled) {
          return;
        }
        setMaskRevisions(response.mask_revisions);
      } catch (error) {
        if (canceled) {
          return;
        }
        setMaskLoadError(getErrorMessage(error, messages.editor.maskLoadErrorFallback));
      } finally {
        if (!canceled) {
          setIsMaskRevisionsLoading(false);
        }
      }
    }

    void loadMaskRevisions();
    return () => {
      canceled = true;
    };
  }, [currentPage, messages.editor.maskLoadErrorFallback, projectId]);

  useEffect(() => {
    if (currentPage === null || !hasPendingPageJobs(jobs)) {
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function pollPageAutomationState() {
      try {
        const [projectResponse, jobsResponse, regionsResponse, maskRevisionsResponse] = await Promise.all([
          getProjectDetail(projectId),
          getPageJobs(projectId, nextPage.id),
          getPageRegions(projectId, nextPage.id),
          getPageMaskRevisions(projectId, nextPage.id),
        ]);
        if (canceled) {
          return;
        }
        setProjectDetail(projectResponse);
        setJobs(jobsResponse.jobs);
        setRegions(regionsResponse.regions);
        setMaskRevisions(maskRevisionsResponse.mask_revisions);
        setSelectedRegionId((currentSelectedRegionId) =>
          regionsResponse.regions.some((region) => region.id === currentSelectedRegionId)
            ? currentSelectedRegionId
            : (regionsResponse.regions[0]?.id ?? null),
        );
        setJobLoadError(null);
        setRegionLoadError(null);
        setMaskLoadError(null);
      } catch (error) {
        if (canceled) {
          return;
        }
        setJobLoadError(getErrorMessage(error, messages.editor.jobLoadErrorFallback));
      }
    }

    void pollPageAutomationState();
    const timer = window.setInterval(() => {
      void pollPageAutomationState();
    }, 3000);

    return () => {
      canceled = true;
      window.clearInterval(timer);
    };
  }, [
    currentPage,
    jobs,
    messages.editor.jobLoadErrorFallback,
    messages.editor.maskLoadErrorFallback,
    projectId,
  ]);

  const selectedRegion =
    regions.find((candidate) => candidate.id === selectedRegionId) ?? null;
  const currentCanvasSize = currentPage
    ? getPageCanvasSize({ width: currentPage.width, height: currentPage.height })
    : null;
  const regionAdjustmentStep = currentPage
    ? getBoundingBoxAdjustmentStep({ width: currentPage.width, height: currentPage.height })
    : 24;
  const selectedRegionMaskRevision =
    selectedRegion === null
      ? null
      : getActiveMaskRevisionForRegion(maskRevisions, selectedRegion.id);
  const approvedActiveMaskRevisionCount = countApprovedActiveMaskRevisions(maskRevisions);

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

  async function handleUpdateRegionBoundingBox(nextBoundingBox: PageRegion["bounding_box"]) {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    setUpdatingRegionId(selectedRegion.id);
    setRegionActionError(null);

    try {
      const response = await updatePageRegion(projectId, currentPage.id, selectedRegion.id, {
        bounding_box: nextBoundingBox,
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

  async function handleQueueRegionDetection() {
    if (currentPage === null) {
      return;
    }

    setIsQueueingDetection(true);
    setJobActionError(null);

    try {
      const response = await createPageJob(projectId, currentPage.id, {
        type: "detect_regions",
      });
      setJobs((currentJobs) => [response.job, ...currentJobs]);
    } catch (error) {
      setJobActionError(getErrorMessage(error, messages.editor.jobCreateErrorFallback));
    } finally {
      setIsQueueingDetection(false);
    }
  }

  async function handleCreateMaskRevisionFromRegion() {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    setIsCreatingMaskRevision(true);
    setMaskActionError(null);

    try {
      const response = await createMaskRevision(
        projectId,
        currentPage.id,
        buildMaskRevisionInputFromRegion(selectedRegion),
      );
      setMaskRevisions((currentMaskRevisions) => {
        const nextMaskRevisions = currentMaskRevisions.filter(
          (maskRevision) =>
            !(maskRevision.region_id === response.mask_revision.region_id && maskRevision.is_active),
        );
        return [...nextMaskRevisions, response.mask_revision];
      });
      await refreshProjectDetailState();
    } catch (error) {
      setMaskActionError(getErrorMessage(error, messages.editor.maskCreateErrorFallback));
    } finally {
      setIsCreatingMaskRevision(false);
    }
  }

  async function handleApproveMaskRevision(maskRevisionId: string) {
    if (currentPage === null) {
      return;
    }

    setUpdatingMaskRevisionId(maskRevisionId);
    setMaskActionError(null);

    try {
      const response = await updateMaskRevision(projectId, currentPage.id, maskRevisionId, {
        approved: true,
      });
      setMaskRevisions((currentMaskRevisions) =>
        currentMaskRevisions.map((maskRevision) =>
          maskRevision.id === response.mask_revision.id ? response.mask_revision : maskRevision,
        ),
      );
      await refreshProjectDetailState();
    } catch (error) {
      setMaskActionError(getErrorMessage(error, messages.editor.maskUpdateErrorFallback));
    } finally {
      setUpdatingMaskRevisionId(null);
    }
  }

  async function handleQueueCleanup() {
    if (currentPage === null) {
      return;
    }

    setIsQueueingCleanup(true);
    setJobActionError(null);

    try {
      const response = await createPageJob(projectId, currentPage.id, {
        type: "generate_cleanup",
      });
      setJobs((currentJobs) => [response.job, ...currentJobs]);
      await refreshProjectDetailState();
    } catch (error) {
      setJobActionError(getErrorMessage(error, messages.editor.jobCreateErrorFallback));
    } finally {
      setIsQueueingCleanup(false);
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
            {maskLoadError ? <p className="notice notice-error">{maskLoadError}</p> : null}
            {maskActionError ? <p className="notice notice-error">{maskActionError}</p> : null}

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
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionConfidenceLabel}</span>
                  <strong>
                    {selectedRegion.confidence === null
                      ? messages.editor.regionConfidenceUnknown
                      : `${Math.round(selectedRegion.confidence * 100)}%`}
                  </strong>
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

                <div className="editor-selection-adjustments">
                  <span className="status-item-label">{messages.editor.adjustBoundsLabel}</span>
                  <div className="editor-adjustment-group">
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            -regionAdjustmentStep,
                            0,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.moveLeftAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            0,
                            -regionAdjustmentStep,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.moveUpAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            0,
                            regionAdjustmentStep,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.moveDownAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            regionAdjustmentStep,
                            0,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.moveRightAction}
                    </button>
                  </div>
                  <div className="editor-adjustment-group">
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            -regionAdjustmentStep,
                            0,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.narrowerAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            regionAdjustmentStep,
                            0,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.widerAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            0,
                            -regionAdjustmentStep,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.shorterAction}
                    </button>
                    <button
                      className="ghost-button"
                      disabled={updatingRegionId === selectedRegion.id}
                      onClick={() =>
                        void handleUpdateRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegion.bounding_box,
                            currentPage,
                            0,
                            regionAdjustmentStep,
                          ),
                        )
                      }
                      type="button"
                    >
                      {messages.editor.tallerAction}
                    </button>
                  </div>
                </div>

                <div className="section-head section-head-compact">
                  <h3 className="section-title">{messages.editor.maskSectionTitle}</h3>
                  <p className="section-copy">{messages.editor.maskSectionCopy}</p>
                </div>

                {isMaskRevisionsLoading ? (
                  <p className="empty-state">{messages.editor.masksLoading}</p>
                ) : selectedRegionMaskRevision ? (
                  <div className="editor-selection-panel editor-mask-panel">
                    <div className="editor-selection-meta">
                      <span className="status-item-label">{messages.editor.maskVersionLabel}</span>
                      <strong>
                        {messages.editor.maskVersionValue.replace(
                          "{version}",
                          String(selectedRegionMaskRevision.version),
                        )}
                      </strong>
                    </div>
                    <div className="editor-selection-meta">
                      <span className="status-item-label">{messages.editor.maskApprovalLabel}</span>
                      <strong>
                        {selectedRegionMaskRevision.approved
                          ? messages.editor.maskApprovedValue
                          : messages.editor.maskPendingValue}
                      </strong>
                    </div>
                    <div className="editor-selection-meta">
                      <span className="status-item-label">{messages.editor.maskPointsLabel}</span>
                      <strong>{selectedRegionMaskRevision.shape.points.length}</strong>
                    </div>
                    <div className="editor-selection-actions">
                      <button
                        className="ghost-button"
                        disabled={isCreatingMaskRevision}
                        onClick={() => void handleCreateMaskRevisionFromRegion()}
                        type="button"
                      >
                        {isCreatingMaskRevision
                          ? messages.editor.creatingMaskAction
                          : messages.editor.refreshMaskFromRegionAction}
                      </button>
                      <button
                        className="secondary-button"
                        disabled={
                          updatingMaskRevisionId === selectedRegionMaskRevision.id
                          || selectedRegionMaskRevision.approved
                        }
                        onClick={() => void handleApproveMaskRevision(selectedRegionMaskRevision.id)}
                        type="button"
                      >
                        {updatingMaskRevisionId === selectedRegionMaskRevision.id
                          ? messages.editor.approvingMaskAction
                          : messages.editor.approveMaskAction}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="editor-selection-panel editor-mask-panel">
                    <p className="empty-state">{messages.editor.masksEmptyForRegion}</p>
                    <button
                      className="primary-button"
                      disabled={isCreatingMaskRevision}
                      onClick={() => void handleCreateMaskRevisionFromRegion()}
                      type="button"
                    >
                      {isCreatingMaskRevision
                        ? messages.editor.creatingMaskAction
                        : messages.editor.createMaskFromRegionAction}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="empty-state">{messages.editor.selectionEmpty}</p>
            )}

            <div className="section-head section-head-compact">
              <h2 className="section-title">{messages.editor.jobsTitle}</h2>
              <p className="section-copy">{messages.editor.jobsCopy}</p>
            </div>

            {jobLoadError ? <p className="notice notice-error">{jobLoadError}</p> : null}
            {jobActionError ? <p className="notice notice-error">{jobActionError}</p> : null}

            <p className="card-description">
              {messages.editor.approvedMasksSummary.replace(
                "{count}",
                String(approvedActiveMaskRevisionCount),
              )}
            </p>

            <div className="editor-selection-actions">
              <button
                className="primary-button"
                disabled={isQueueingDetection}
                onClick={() => void handleQueueRegionDetection()}
                type="button"
              >
                {isQueueingDetection
                  ? messages.editor.queuingDetectionAction
                  : messages.editor.queueDetectionAction}
              </button>
              <button
                className="secondary-button"
                disabled={isQueueingCleanup || !hasApprovedActiveMaskRevisions(maskRevisions)}
                onClick={() => void handleQueueCleanup()}
                type="button"
              >
                {isQueueingCleanup
                  ? messages.editor.queuingCleanupAction
                  : messages.editor.queueCleanupAction}
              </button>
            </div>

            {isJobsLoading ? (
              <p className="empty-state">{messages.editor.jobsLoading}</p>
            ) : jobs.length === 0 ? (
              <p className="empty-state">{messages.editor.jobsEmpty}</p>
            ) : (
              <div className="editor-job-list">
                {jobs.map((job) => (
                  <article className="editor-job-card" key={job.id}>
                    <div className="editor-region-card-header">
                      <span className="card-step">{messages.editor.jobTypeLabels[job.type]}</span>
                      <span className={`editor-job-state-pill editor-job-state-pill-${job.status}`}>
                        {messages.editor.jobStatusLabels[job.status]}
                      </span>
                    </div>
                    <strong>{job.id}</strong>
                    <p className="card-description">{job.created_at}</p>
                  </article>
                ))}
              </div>
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

            <div className="section-head section-head-compact">
              <h2 className="section-title">{messages.editor.cleanupPreviewTitle}</h2>
              <p className="section-copy">{messages.editor.cleanupPreviewCopy}</p>
            </div>

            {currentPage.active_cleaned_asset_path ? (
              <div className="editor-compare-grid">
                <article className="editor-compare-card">
                  <span className="card-step">{messages.editor.originalPreviewLabel}</span>
                  <img
                    alt={`${currentPage.file_name} original`}
                    className="editor-compare-image"
                    src={resolveApiAssetUrl(currentPage.original_asset_path)}
                  />
                </article>
                <article className="editor-compare-card">
                  <span className="card-step">{messages.editor.cleanedPreviewLabel}</span>
                  <img
                    alt={`${currentPage.file_name} cleaned`}
                    className="editor-compare-image"
                    src={resolveApiAssetUrl(currentPage.active_cleaned_asset_path)}
                  />
                </article>
              </div>
            ) : (
              <p className="empty-state">{messages.editor.cleanupPreviewEmpty}</p>
            )}
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
