"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";

import type { AppMessages } from "../i18n/index.ts";
import type { SupportedUiLocale } from "../i18n/config.ts";
import {
  ApiClientError,
  createMaskRevision,
  createManualDialogue,
  createPageJob,
  createPageRegion,
  deletePageRegion,
  getPageAssignments,
  getPageDialogues,
  getPageJobs,
  getPageMaskRevisions,
  getPagePlacements,
  getPageRegions,
  getPageTranslations,
  getProjectDetail,
  resetPageRegions,
  resolveApiAssetUrl,
  updateManualDialogue,
  updateMaskRevision,
  upsertPageAssignment,
  upsertPagePlacement,
  upsertPageTranslation,
  updatePageRegion,
} from "../features/projects/api.ts";
import {
  countAvailableMatchingRegions,
  countOcrCandidateRegions,
  countUnassignedDialogues,
} from "../features/projects/automation.ts";
import {
  hasPendingPageJobs,
  hasPendingPageJobType,
  hasQueuedPageJobs,
  hasRunningPageJobs,
} from "../features/projects/jobs.ts";
import {
  buildJpegExportFileName,
  buildPdfExportFileName,
  buildPsdExportFileName,
  exportPageAsJpeg,
  exportPageAsPdf,
  exportPageAsPsd,
  getPreferredExportAssetPath,
} from "../features/projects/export.ts";
import {
  buildMaskRevisionInputFromRegion,
  countApprovedActiveMaskRevisions,
  getCleanupMaskCandidateRegions,
  getActiveMaskRevisionForRegion,
  hasApprovedActiveMaskRevisions,
} from "../features/projects/masks.ts";
import {
  buildDefaultPlacementInput,
  buildTextPreviewEntries,
  getNextReadingOrder,
  getPlacementOverlayStyle,
} from "../features/projects/text.ts";
import {
  buildBalloonGroupOverlays,
  buildDefaultRegionInput,
  buildPanelOverlays,
  buildRegionDisplayLabelLookup,
  formatBalloonGroupOverlayLabel,
  formatRegionBounds,
  formatPanelOverlayLabel,
  getBoundingBoxOverlayStyle,
  getBoundingBoxAdjustmentStep,
  getPageCanvasSize,
  getRegionAreaBoundingBox,
  moveBoundingBox,
  refineTextAreaToDarkPixels,
  resizeBoundingBox,
  resizeBoundingBoxFromHandle,
} from "../features/projects/regions.ts";
import type { RegionAreaKind, ResizeHandle } from "../features/projects/regions.ts";
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
type PageDialoguesResponse = Awaited<ReturnType<typeof getPageDialogues>>;
type PageDialogue = PageDialoguesResponse["dialogues"][number];
type PageTranslationsResponse = Awaited<ReturnType<typeof getPageTranslations>>;
type PageTranslation = PageTranslationsResponse["translations"][number];
type PageAssignmentsResponse = Awaited<ReturnType<typeof getPageAssignments>>;
type PageAssignment = PageAssignmentsResponse["assignments"][number];
type PagePlacementsResponse = Awaited<ReturnType<typeof getPagePlacements>>;
type PagePlacement = PagePlacementsResponse["placements"][number];
type RegionBoundingBox = PageRegion["bounding_box"];

type ActiveRegionTransform = {
  regionId: string;
  area: RegionAreaKind;
  mode: "move" | "resize";
  handle?: ResizeHandle;
  startClientX: number;
  startClientY: number;
  initialBox: RegionBoundingBox;
};

type RegionAreaDraft = {
  regionId: string;
  area: RegionAreaKind;
  box: RegionBoundingBox;
};

type PageImageRaster = {
  width: number;
  height: number;
  data: Uint8ClampedArray;
};

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

function getRegionOverlayClassName(
  region: PageRegion,
  area: RegionAreaKind,
  isSelected: boolean,
  isActiveArea: boolean,
) {
  const baseClass = `editor-region-overlay editor-region-overlay-${region.state}`;
  const areaClass =
    area === "text_area"
      ? "editor-region-overlay-text-area"
      : "editor-region-overlay-context-area";
  const selectedClass = isSelected ? " editor-region-overlay-selected" : "";
  const activeAreaClass = isActiveArea ? " editor-region-overlay-active-area" : "";
  return `${baseClass} ${areaClass}${selectedClass}${activeAreaClass}`;
}

function areBoundingBoxesEqual(left: RegionBoundingBox, right: RegionBoundingBox) {
  return (
    left.x === right.x
    && left.y === right.y
    && left.width === right.width
    && left.height === right.height
  );
}

async function loadPageImageRaster(imageSrc: string): Promise<PageImageRaster> {
  const image = new Image();
  image.crossOrigin = "anonymous";

  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("PAGE_IMAGE_LOAD_FAILED"));
    image.src = imageSrc;
  });

  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (context === null) {
    throw new Error("PAGE_IMAGE_CONTEXT_UNAVAILABLE");
  }

  context.drawImage(image, 0, 0);
  const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
  return {
    width: imageData.width,
    height: imageData.height,
    data: imageData.data,
  };
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
  const [dialogues, setDialogues] = useState<PageDialogue[]>([]);
  const [translations, setTranslations] = useState<PageTranslation[]>([]);
  const [assignments, setAssignments] = useState<PageAssignment[]>([]);
  const [placements, setPlacements] = useState<PagePlacement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegionsLoading, setIsRegionsLoading] = useState(false);
  const [isMaskRevisionsLoading, setIsMaskRevisionsLoading] = useState(false);
  const [isTextLoading, setIsTextLoading] = useState(false);
  const [isCreatingRegion, setIsCreatingRegion] = useState(false);
  const [isJobsLoading, setIsJobsLoading] = useState(false);
  const [isQueueingDetection, setIsQueueingDetection] = useState(false);
  const [isQueueingCleanup, setIsQueueingCleanup] = useState(false);
  const [isQueueingOcr, setIsQueueingOcr] = useState(false);
  const [isQueueingTranslation, setIsQueueingTranslation] = useState(false);
  const [isQueueingMatching, setIsQueueingMatching] = useState(false);
  const [isResettingRegions, setIsResettingRegions] = useState(false);
  const [isCreatingMaskRevision, setIsCreatingMaskRevision] = useState(false);
  const [isSavingDialogue, setIsSavingDialogue] = useState(false);
  const [isExportingJpeg, setIsExportingJpeg] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingPsd, setIsExportingPsd] = useState(false);
  const [isRefiningTextArea, setIsRefiningTextArea] = useState(false);
  const [deletingRegionId, setDeletingRegionId] = useState<string | null>(null);
  const [updatingRegionId, setUpdatingRegionId] = useState<string | null>(null);
  const [updatingMaskRevisionId, setUpdatingMaskRevisionId] = useState<string | null>(null);
  const [updatingPlacementId, setUpdatingPlacementId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [regionLoadError, setRegionLoadError] = useState<string | null>(null);
  const [regionActionError, setRegionActionError] = useState<string | null>(null);
  const [jobLoadError, setJobLoadError] = useState<string | null>(null);
  const [jobActionError, setJobActionError] = useState<string | null>(null);
  const [maskLoadError, setMaskLoadError] = useState<string | null>(null);
  const [maskActionError, setMaskActionError] = useState<string | null>(null);
  const [textLoadError, setTextLoadError] = useState<string | null>(null);
  const [textActionError, setTextActionError] = useState<string | null>(null);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
  const [selectedDialogueId, setSelectedDialogueId] = useState<string | null>(null);
  const [dialogueDraft, setDialogueDraft] = useState("");
  const [translationDraft, setTranslationDraft] = useState("");
  const [showContextAreas, setShowContextAreas] = useState(true);
  const [showTextAreas, setShowTextAreas] = useState(true);
  const [showPanelAreas, setShowPanelAreas] = useState(false);
  const [showBalloonGroups, setShowBalloonGroups] = useState(false);
  const [showOverlayLabels, setShowOverlayLabels] = useState(true);
  const [selectedRegionArea, setSelectedRegionArea] = useState<RegionAreaKind>("context_area");
  const [activeRegionTransform, setActiveRegionTransform] = useState<ActiveRegionTransform | null>(null);
  const [regionAreaDraft, setRegionAreaDraft] = useState<RegionAreaDraft | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const pageImageRasterRef = useRef<{ src: string; raster: PageImageRaster } | null>(null);

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

  function handleSelectRegion(regionId: string, area: RegionAreaKind = "context_area") {
    setSelectedRegionId(regionId);
    setSelectedRegionArea(area);
  }

  function getRegionAreaDisplayBoundingBox(
    region: PageRegion,
    area: RegionAreaKind,
  ): RegionBoundingBox {
    if (regionAreaDraft?.regionId === region.id && regionAreaDraft.area === area) {
      return regionAreaDraft.box;
    }
    return getRegionAreaBoundingBox(region, area);
  }

  function buildTransformedRegionBox(
    transform: ActiveRegionTransform,
    clientX: number,
    clientY: number,
  ): RegionBoundingBox {
    if (currentPage === null || stageRef.current === null) {
      return transform.initialBox;
    }

    const stageRect = stageRef.current.getBoundingClientRect();
    if (stageRect.width === 0 || stageRect.height === 0) {
      return transform.initialBox;
    }

    const pageWidth = currentPage.width ?? 1000;
    const pageHeight = currentPage.height ?? 1400;
    const dx = ((clientX - transform.startClientX) / stageRect.width) * pageWidth;
    const dy = ((clientY - transform.startClientY) / stageRect.height) * pageHeight;

    if (transform.mode === "resize" && transform.handle !== undefined) {
      return resizeBoundingBoxFromHandle(
        transform.initialBox,
        currentPage,
        transform.handle,
        dx,
        dy,
      );
    }

    return moveBoundingBox(transform.initialBox, currentPage, dx, dy);
  }

  async function refreshProjectDetailState() {
    const response = await getProjectDetail(projectId);
    setProjectDetail(response);
    return response;
  }

  async function fetchTextStateSnapshot(nextPageId: string) {
    const [dialoguesResponse, translationsResponse, assignmentsResponse, placementsResponse] =
      await Promise.all([
        getPageDialogues(projectId, nextPageId),
        getPageTranslations(projectId, nextPageId),
        getPageAssignments(projectId, nextPageId),
        getPagePlacements(projectId, nextPageId),
      ]);
    return {
      dialogues: dialoguesResponse.dialogues,
      translations: translationsResponse.translations,
      assignments: assignmentsResponse.assignments,
      placements: placementsResponse.placements,
    };
  }

  async function fetchPageEditorStateSnapshot(nextPageId: string) {
    const [
      projectResponse,
      jobsResponse,
      regionsResponse,
      maskRevisionsResponse,
      dialoguesResponse,
      translationsResponse,
      assignmentsResponse,
      placementsResponse,
    ] = await Promise.all([
      getProjectDetail(projectId),
      getPageJobs(projectId, nextPageId),
      getPageRegions(projectId, nextPageId),
      getPageMaskRevisions(projectId, nextPageId),
      getPageDialogues(projectId, nextPageId),
      getPageTranslations(projectId, nextPageId),
      getPageAssignments(projectId, nextPageId),
      getPagePlacements(projectId, nextPageId),
    ]);

    return {
      projectResponse,
      jobsResponse,
      regionsResponse,
      maskRevisionsResponse,
      dialoguesResponse,
      translationsResponse,
      assignmentsResponse,
      placementsResponse,
    };
  }

  function applyPageEditorStateSnapshot(
    snapshot: Awaited<ReturnType<typeof fetchPageEditorStateSnapshot>>,
  ) {
    const {
      projectResponse,
      jobsResponse,
      regionsResponse,
      maskRevisionsResponse,
      dialoguesResponse,
      translationsResponse,
      assignmentsResponse,
      placementsResponse,
    } = snapshot;

    setProjectDetail(projectResponse);
    setJobs(jobsResponse.jobs);
    setRegions(regionsResponse.regions);
    setMaskRevisions(maskRevisionsResponse.mask_revisions);
    setDialogues(dialoguesResponse.dialogues);
    setTranslations(translationsResponse.translations);
    setAssignments(assignmentsResponse.assignments);
    setPlacements(placementsResponse.placements);
    setSelectedRegionId((currentSelectedRegionId) =>
      regionsResponse.regions.some((region) => region.id === currentSelectedRegionId)
        ? currentSelectedRegionId
        : (regionsResponse.regions[0]?.id ?? null),
    );
    setSelectedDialogueId((currentSelectedDialogueId) =>
      dialoguesResponse.dialogues.some((dialogue) => dialogue.id === currentSelectedDialogueId)
        ? currentSelectedDialogueId
        : (dialoguesResponse.dialogues[0]?.id ?? null),
    );
    setJobLoadError(null);
    setRegionLoadError(null);
    setMaskLoadError(null);
    setTextLoadError(null);
  }

  async function refreshPageEditorState(nextPageId: string) {
    const snapshot = await fetchPageEditorStateSnapshot(nextPageId);
    applyPageEditorStateSnapshot(snapshot);
  }

  useEffect(() => {
    if (currentPage === null) {
      setRegions([]);
      setJobs([]);
      setMaskRevisions([]);
      setDialogues([]);
      setTranslations([]);
      setAssignments([]);
      setPlacements([]);
      setSelectedRegionId(null);
      setSelectedDialogueId(null);
      setDialogueDraft("");
      setTranslationDraft("");
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
    if (currentPage === null) {
      setDialogues([]);
      setTranslations([]);
      setAssignments([]);
      setPlacements([]);
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function loadTextState() {
      setIsTextLoading(true);
      setTextLoadError(null);
      try {
        const response = await fetchTextStateSnapshot(nextPage.id);
        if (canceled) {
          return;
        }
        setDialogues(response.dialogues);
        setTranslations(response.translations);
        setAssignments(response.assignments);
        setPlacements(response.placements);
        setSelectedDialogueId((currentSelectedDialogueId) =>
          response.dialogues.some((dialogue) => dialogue.id === currentSelectedDialogueId)
            ? currentSelectedDialogueId
            : (response.dialogues[0]?.id ?? null),
        );
      } catch (error) {
        if (canceled) {
          return;
        }
        setTextLoadError(getErrorMessage(error, messages.editor.textLoadErrorFallback));
      } finally {
        if (!canceled) {
          setIsTextLoading(false);
        }
      }
    }

    void loadTextState();
    return () => {
      canceled = true;
    };
  }, [currentPage, messages.editor.textLoadErrorFallback, projectId]);

  useEffect(() => {
    if (currentPage === null || !hasPendingPageJobs(jobs)) {
      return;
    }

    const nextPage = currentPage;
    let canceled = false;

    async function pollPageAutomationState() {
      try {
        const snapshot = await fetchPageEditorStateSnapshot(nextPage.id);
        if (canceled) {
          return;
        }
        applyPageEditorStateSnapshot(snapshot);
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
    messages.editor.textLoadErrorFallback,
    projectId,
  ]);

  useEffect(() => {
    const selectedDialogue =
      dialogues.find((candidate) => candidate.id === selectedDialogueId) ?? null;
    if (selectedDialogue === null) {
      setDialogueDraft("");
      setTranslationDraft("");
      return;
    }

    const selectedTranslation =
      translations.find((candidate) => candidate.dialogue_id === selectedDialogue.id) ?? null;
    setDialogueDraft(selectedDialogue.content);
    setTranslationDraft(selectedTranslation?.content ?? "");
  }, [dialogues, selectedDialogueId, translations]);

  useEffect(() => {
    if (activeRegionTransform === null || currentPage === null) {
      return;
    }
    const transform = activeRegionTransform;

    function handleWindowMouseMove(event: MouseEvent) {
      const nextBoundingBox = buildTransformedRegionBox(
        transform,
        event.clientX,
        event.clientY,
      );
      setRegionAreaDraft({
        regionId: transform.regionId,
        area: transform.area,
        box: nextBoundingBox,
      });
    }

    function handleWindowMouseUp(event: MouseEvent) {
      const nextBoundingBox = buildTransformedRegionBox(
        transform,
        event.clientX,
        event.clientY,
      );
      setActiveRegionTransform(null);
      setRegionAreaDraft(null);
      if (areBoundingBoxesEqual(nextBoundingBox, transform.initialBox)) {
        return;
      }
      void handleUpdateRegionAreaBoundingBox(
        transform.regionId,
        transform.area,
        nextBoundingBox,
      );
    }

    window.addEventListener("mousemove", handleWindowMouseMove);
    window.addEventListener("mouseup", handleWindowMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleWindowMouseMove);
      window.removeEventListener("mouseup", handleWindowMouseUp);
    };
  }, [activeRegionTransform, currentPage]);

  const selectedRegion =
    regions.find((candidate) => candidate.id === selectedRegionId) ?? null;
  const orderedRegions = [...regions].sort((left, right) => {
    const leftOrder = left.global_reading_order ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = right.global_reading_order ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }

    const leftPanelOrder = left.panel_order ?? Number.MAX_SAFE_INTEGER;
    const rightPanelOrder = right.panel_order ?? Number.MAX_SAFE_INTEGER;
    if (leftPanelOrder != rightPanelOrder) {
      return leftPanelOrder - rightPanelOrder;
    }

    const leftBalloonGroupOrder = left.balloon_group_order ?? Number.MAX_SAFE_INTEGER;
    const rightBalloonGroupOrder = right.balloon_group_order ?? Number.MAX_SAFE_INTEGER;
    if (leftBalloonGroupOrder !== rightBalloonGroupOrder) {
      return leftBalloonGroupOrder - rightBalloonGroupOrder;
    }

    const leftOrderInBalloonGroup = left.order_in_balloon_group ?? Number.MAX_SAFE_INTEGER;
    const rightOrderInBalloonGroup = right.order_in_balloon_group ?? Number.MAX_SAFE_INTEGER;
    if (leftOrderInBalloonGroup !== rightOrderInBalloonGroup) {
      return leftOrderInBalloonGroup - rightOrderInBalloonGroup;
    }

    const leftOrderInPanel = left.order_in_panel ?? Number.MAX_SAFE_INTEGER;
    const rightOrderInPanel = right.order_in_panel ?? Number.MAX_SAFE_INTEGER;
    if (leftOrderInPanel !== rightOrderInPanel) {
      return leftOrderInPanel - rightOrderInPanel;
    }

    if (left.bounding_box.y !== right.bounding_box.y) {
      return left.bounding_box.y - right.bounding_box.y;
    }
    return left.bounding_box.x - right.bounding_box.x;
  });
  const selectedRegionOrderIndex =
    selectedRegion === null
      ? -1
      : orderedRegions.findIndex((candidate) => candidate.id === selectedRegion.id);
  const regionDisplayLabels = buildRegionDisplayLabelLookup(orderedRegions);
  const selectedRegionDisplayLabel =
    selectedRegion === null
      ? null
      : (regionDisplayLabels.get(selectedRegion.id)
        ?? `R${String(selectedRegionOrderIndex + 1).padStart(2, "0")}`);
  const selectedDialogue =
    dialogues.find((candidate) => candidate.id === selectedDialogueId) ?? null;
  const selectedDialogueAssignment =
    selectedDialogue === null
      ? null
      : assignments.find((candidate) => candidate.dialogue_id === selectedDialogue.id) ?? null;
  const selectedDialoguePlacement =
    selectedDialogueAssignment === null
      ? null
      : placements.find((candidate) => candidate.assignment_id === selectedDialogueAssignment.id) ?? null;
  const currentCanvasSize = currentPage
    ? getPageCanvasSize({ width: currentPage.width, height: currentPage.height })
    : null;
  const panelOverlays = buildPanelOverlays(orderedRegions);
  const balloonGroupOverlays = buildBalloonGroupOverlays(orderedRegions);
  const regionAdjustmentStep = currentPage
    ? getBoundingBoxAdjustmentStep({ width: currentPage.width, height: currentPage.height })
    : 24;
  const selectedRegionMaskRevision =
    selectedRegion === null
      ? null
      : getActiveMaskRevisionForRegion(maskRevisions, selectedRegion.id);
  const selectedRegionAreaBoundingBox =
    selectedRegion === null
      ? null
      : getRegionAreaDisplayBoundingBox(selectedRegion, selectedRegionArea);
  const approvedActiveMaskRevisionCount = countApprovedActiveMaskRevisions(maskRevisions);
  const ocrCandidateRegionCount = countOcrCandidateRegions(regions);
  const availableMatchingRegionCount = countAvailableMatchingRegions(regions, assignments);
  const unassignedDialogueCount = countUnassignedDialogues(dialogues, assignments);
  const textPreviewEntries = buildTextPreviewEntries({
    dialogues,
    translations,
    assignments,
    placements,
  });
  const hasQueuedJobsForPage = hasQueuedPageJobs(jobs);
  const hasRunningJobsForPage = hasRunningPageJobs(jobs);
  const hasPendingDetectionJob = hasPendingPageJobType(jobs, "detect_regions");
  const hasPendingCleanupJob = hasPendingPageJobType(jobs, "generate_cleanup");
  const hasPendingOcrJob = hasPendingPageJobType(jobs, "run_ocr");
  const hasPendingTranslationJob = hasPendingPageJobType(jobs, "generate_translation");
  const hasPendingMatchingJob = hasPendingPageJobType(jobs, "match_dialogue");

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
      handleSelectRegion(response.region.id, "context_area");
      setShowContextAreas(true);
      setShowTextAreas(true);
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

  async function handleMoveSelectedRegionReadingOrder(offset: -1 | 1) {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    const currentIndex = orderedRegions.findIndex((region) => region.id === selectedRegion.id);
    if (currentIndex === -1) {
      return;
    }

    const nextPosition = Math.max(
      1,
      Math.min(orderedRegions.length, currentIndex + 1 + offset),
    );
    if (nextPosition === currentIndex + 1) {
      return;
    }

    setUpdatingRegionId(selectedRegion.id);
    setRegionActionError(null);

    try {
      await updatePageRegion(projectId, currentPage.id, selectedRegion.id, {
        global_reading_order: nextPosition,
      });
      const refreshedRegions = await getPageRegions(projectId, currentPage.id);
      setRegions(refreshedRegions.regions);
      handleSelectRegion(selectedRegion.id, selectedRegionArea);
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionUpdateErrorFallback));
    } finally {
      setUpdatingRegionId(null);
    }
  }

  async function handleUpdateRegionAreaBoundingBox(
    regionId: string,
    area: RegionAreaKind,
    nextBoundingBox: RegionBoundingBox,
  ) {
    if (currentPage === null) {
      return;
    }

    setUpdatingRegionId(regionId);
    setRegionActionError(null);

    try {
      const response = await updatePageRegion(projectId, currentPage.id, regionId, (
        area === "text_area"
          ? {
              bounding_box: nextBoundingBox,
              text_area: nextBoundingBox,
            }
          : {
              context_area: nextBoundingBox,
            }
      ));
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

  async function handleUpdateSelectedRegionBoundingBox(nextBoundingBox: RegionBoundingBox) {
    if (selectedRegion === null) {
      return;
    }
    await handleUpdateRegionAreaBoundingBox(
      selectedRegion.id,
      selectedRegionArea,
      nextBoundingBox,
    );
  }

  async function getCurrentPageImageRaster() {
    if (currentPage === null) {
      throw new Error("PAGE_IMAGE_UNAVAILABLE");
    }

    const imageSrc = resolveApiAssetUrl(currentPage.original_asset_path);
    if (pageImageRasterRef.current?.src === imageSrc) {
      return pageImageRasterRef.current.raster;
    }

    const raster = await loadPageImageRaster(imageSrc);
    pageImageRasterRef.current = {
      src: imageSrc,
      raster,
    };
    return raster;
  }

  async function handleRefineSelectedTextArea() {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    setIsRefiningTextArea(true);
    setUpdatingRegionId(selectedRegion.id);
    setRegionActionError(null);

    try {
      const raster = await getCurrentPageImageRaster();
      const nextTextArea = refineTextAreaToDarkPixels(
        raster,
        getRegionAreaDisplayBoundingBox(selectedRegion, "text_area"),
      );
      const currentTextArea = getRegionAreaBoundingBox(selectedRegion, "text_area");
      if (areBoundingBoxesEqual(nextTextArea, currentTextArea)) {
        setSelectedRegionArea("text_area");
        return;
      }

      const response = await updatePageRegion(projectId, currentPage.id, selectedRegion.id, {
        bounding_box: nextTextArea,
        text_area: nextTextArea,
      });
      setRegions((currentRegions) =>
        currentRegions.map((region) =>
          region.id === response.region.id ? response.region : region,
        ),
      );
      setSelectedRegionArea("text_area");
      setShowTextAreas(true);
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionUpdateErrorFallback));
    } finally {
      setIsRefiningTextArea(false);
      setUpdatingRegionId(null);
    }
  }

  function handleRegionAreaMouseDown(
    event: ReactMouseEvent<HTMLElement>,
    region: PageRegion,
    area: RegionAreaKind,
  ) {
    if (currentPage === null || updatingRegionId === region.id || hasRunningJobsForPage) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    const initialBox = getRegionAreaDisplayBoundingBox(region, area);
    handleSelectRegion(region.id, area);
    setRegionAreaDraft({
      regionId: region.id,
      area,
      box: initialBox,
    });
    setActiveRegionTransform({
      regionId: region.id,
      area,
      mode: "move",
      startClientX: event.clientX,
      startClientY: event.clientY,
      initialBox,
    });
  }

  function handleRegionResizeHandleMouseDown(
    event: ReactMouseEvent<HTMLButtonElement>,
    region: PageRegion,
    area: RegionAreaKind,
    handle: ResizeHandle,
  ) {
    if (currentPage === null || updatingRegionId === region.id || hasRunningJobsForPage) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    const initialBox = getRegionAreaDisplayBoundingBox(region, area);
    handleSelectRegion(region.id, area);
    setRegionAreaDraft({
      regionId: region.id,
      area,
      box: initialBox,
    });
    setActiveRegionTransform({
      regionId: region.id,
      area,
      mode: "resize",
      handle,
      startClientX: event.clientX,
      startClientY: event.clientY,
      initialBox,
    });
  }

  async function handleDeleteSelectedRegion() {
    if (currentPage === null || selectedRegion === null) {
      return;
    }

    setDeletingRegionId(selectedRegion.id);
    setRegionActionError(null);

    try {
      await deletePageRegion(projectId, currentPage.id, selectedRegion.id);
      await refreshPageEditorState(currentPage.id);
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionDeleteErrorFallback));
    } finally {
      setDeletingRegionId(null);
    }
  }

  async function handleResetRegions() {
    if (currentPage === null) {
      return;
    }

    setIsResettingRegions(true);
    setRegionActionError(null);

    try {
      await resetPageRegions(projectId, currentPage.id);
      await refreshPageEditorState(currentPage.id);
    } catch (error) {
      setRegionActionError(getErrorMessage(error, messages.editor.regionResetErrorFallback));
    } finally {
      setIsResettingRegions(false);
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
    setMaskActionError(null);

    try {
      const cleanupCandidateRegions = getCleanupMaskCandidateRegions(regions);
      if (cleanupCandidateRegions.length === 0) {
        throw new Error(messages.editor.cleanupRequiresRegionsFallback);
      }

      let nextMaskRevisions = [...maskRevisions];
      for (const region of cleanupCandidateRegions) {
        const activeMaskRevision = getActiveMaskRevisionForRegion(nextMaskRevisions, region.id);
        if (activeMaskRevision?.approved) {
          continue;
        }

        if (activeMaskRevision !== null) {
          const approvedMaskResponse = await updateMaskRevision(
            projectId,
            currentPage.id,
            activeMaskRevision.id,
            { approved: true },
          );
          nextMaskRevisions = nextMaskRevisions.map((maskRevision) =>
            maskRevision.id === approvedMaskResponse.mask_revision.id
              ? approvedMaskResponse.mask_revision
              : maskRevision,
          );
          continue;
        }

        const createdMaskResponse = await createMaskRevision(
          projectId,
          currentPage.id,
          buildMaskRevisionInputFromRegion(region),
        );
        nextMaskRevisions = [
          ...nextMaskRevisions.filter(
            (maskRevision) =>
              !(maskRevision.region_id === createdMaskResponse.mask_revision.region_id && maskRevision.is_active),
          ),
          createdMaskResponse.mask_revision,
        ];
        const approvedMaskResponse = await updateMaskRevision(
          projectId,
          currentPage.id,
          createdMaskResponse.mask_revision.id,
          { approved: true },
        );
        nextMaskRevisions = nextMaskRevisions.map((maskRevision) =>
          maskRevision.id === approvedMaskResponse.mask_revision.id
            ? approvedMaskResponse.mask_revision
            : maskRevision,
        );
      }

      setMaskRevisions(nextMaskRevisions);
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

  async function handleQueueOcr() {
    if (currentPage === null) {
      return;
    }

    setIsQueueingOcr(true);
    setJobActionError(null);

    try {
      const response = await createPageJob(projectId, currentPage.id, {
        type: "run_ocr",
      });
      setJobs((currentJobs) => [response.job, ...currentJobs]);
      await refreshProjectDetailState();
    } catch (error) {
      setJobActionError(getErrorMessage(error, messages.editor.jobCreateErrorFallback));
    } finally {
      setIsQueueingOcr(false);
    }
  }

  async function handleQueueAutomaticTranslation() {
    if (currentPage === null) {
      return;
    }

    setIsQueueingTranslation(true);
    setJobActionError(null);

    try {
      const response = await createPageJob(projectId, currentPage.id, {
        type: "generate_translation",
      });
      setJobs((currentJobs) => [response.job, ...currentJobs]);
    } catch (error) {
      setJobActionError(getErrorMessage(error, messages.editor.jobCreateErrorFallback));
    } finally {
      setIsQueueingTranslation(false);
    }
  }

  async function handleQueueDialogueMatching() {
    if (currentPage === null) {
      return;
    }

    setIsQueueingMatching(true);
    setJobActionError(null);

    try {
      const response = await createPageJob(projectId, currentPage.id, {
        type: "match_dialogue",
      });
      setJobs((currentJobs) => [response.job, ...currentJobs]);
    } catch (error) {
      setJobActionError(getErrorMessage(error, messages.editor.jobCreateErrorFallback));
    } finally {
      setIsQueueingMatching(false);
    }
  }

  function handleStartNewDialogue() {
    setSelectedDialogueId(null);
    setDialogueDraft("");
    setTranslationDraft("");
  }

  async function handleSaveDialogueWorkflow() {
    if (currentPage === null || projectDetail === null) {
      return;
    }

    const trimmedSourceText = dialogueDraft.trim();
    const trimmedTranslationText = translationDraft.trim();
    if (trimmedSourceText.length === 0) {
      setTextActionError(messages.editor.sourceTextRequired);
      return;
    }

    setIsSavingDialogue(true);
    setTextActionError(null);

    try {
      const readingOrder =
        selectedDialogue?.reading_order ?? getNextReadingOrder(dialogues);
      const dialogueResponse = selectedDialogue
        ? await updateManualDialogue(projectId, currentPage.id, selectedDialogue.id, {
            page_id: currentPage.id,
            content: trimmedSourceText,
            source_language: projectDetail.project.source_language,
            reading_order: readingOrder,
          })
        : await createManualDialogue(projectId, currentPage.id, {
            page_id: currentPage.id,
            content: trimmedSourceText,
            source_language: projectDetail.project.source_language,
            reading_order: readingOrder,
          });

      const translationResponse = await upsertPageTranslation(projectId, currentPage.id, {
        dialogue_id: dialogueResponse.dialogue.id,
        target_language: projectDetail.project.target_language,
        text_direction: projectDetail.project.target_text_direction,
        content: trimmedTranslationText,
        status: "approved",
      });

      if (selectedRegion !== null) {
        const assignmentResponse = await upsertPageAssignment(projectId, currentPage.id, {
          dialogue_id: dialogueResponse.dialogue.id,
          region_id: selectedRegion.id,
          origin: "manual",
          approved: true,
        });
        const existingPlacement = placements.find(
          (placement) => placement.assignment_id === assignmentResponse.assignment.id,
        );
        const placementInput =
          existingPlacement === undefined
            ? buildDefaultPlacementInput({
                assignmentId: assignmentResponse.assignment.id,
                region: selectedRegion,
                targetLanguage: projectDetail.project.target_language,
                textDirection: projectDetail.project.target_text_direction,
              })
            : {
                assignment_id: assignmentResponse.assignment.id,
                text_box: existingPlacement.text_box,
                style: existingPlacement.style,
              };
        await upsertPagePlacement(projectId, currentPage.id, placementInput);
      }

      await refreshProjectDetailState();
      const refreshedTextState = await fetchTextStateSnapshot(currentPage.id);
      setDialogues(refreshedTextState.dialogues);
      setTranslations(refreshedTextState.translations);
      setAssignments(refreshedTextState.assignments);
      setPlacements(refreshedTextState.placements);
      setSelectedDialogueId(dialogueResponse.dialogue.id);
      setDialogueDraft(dialogueResponse.dialogue.content);
      setTranslationDraft(translationResponse.translation.content);
      setSelectedDialogueId((currentSelectedDialogueId) =>
        refreshedTextState.dialogues.some((dialogue) => dialogue.id === currentSelectedDialogueId)
          ? currentSelectedDialogueId
          : dialogueResponse.dialogue.id,
      );
    } catch (error) {
      setTextActionError(getErrorMessage(error, messages.editor.textSaveErrorFallback));
    } finally {
      setIsSavingDialogue(false);
    }
  }

  async function handleUpdatePlacementBoundingBox(nextBoundingBox: PagePlacement["text_box"]) {
    if (
      currentPage === null
      || selectedDialogueAssignment === null
      || selectedDialoguePlacement === null
    ) {
      return;
    }

    setUpdatingPlacementId(selectedDialoguePlacement.id);
    setTextActionError(null);

    try {
      const response = await upsertPagePlacement(projectId, currentPage.id, {
        assignment_id: selectedDialogueAssignment.id,
        text_box: nextBoundingBox,
        style: selectedDialoguePlacement.style,
      });
      setPlacements((currentPlacements) =>
        currentPlacements.map((placement) =>
          placement.id === response.placement.id ? response.placement : placement,
        ),
      );
      await refreshProjectDetailState();
    } catch (error) {
      setTextActionError(getErrorMessage(error, messages.editor.textSaveErrorFallback));
    } finally {
      setUpdatingPlacementId(null);
    }
  }

  async function handleExportCurrentPageJpeg() {
    if (currentPage === null) {
      return;
    }

    setIsExportingJpeg(true);
    setTextActionError(null);

    try {
      await exportPageAsJpeg({
        imageSrc: resolveApiAssetUrl(getPreferredExportAssetPath(currentPage)),
        fileName: buildJpegExportFileName(currentPage.file_name),
        width: currentPage.width,
        height: currentPage.height,
        entries: textPreviewEntries,
      });
    } catch (error) {
      setTextActionError(getErrorMessage(error, messages.editor.exportJpegErrorFallback));
    } finally {
      setIsExportingJpeg(false);
    }
  }

  async function handleExportCurrentPagePdf() {
    if (currentPage === null) {
      return;
    }

    setIsExportingPdf(true);
    setTextActionError(null);

    try {
      await exportPageAsPdf({
        imageSrc: resolveApiAssetUrl(getPreferredExportAssetPath(currentPage)),
        fileName: buildPdfExportFileName(currentPage.file_name),
        width: currentPage.width,
        height: currentPage.height,
        entries: textPreviewEntries,
      });
    } catch (error) {
      setTextActionError(getErrorMessage(error, messages.editor.exportPdfErrorFallback));
    } finally {
      setIsExportingPdf(false);
    }
  }

  async function handleExportCurrentPagePsd() {
    if (currentPage === null) {
      return;
    }

    setIsExportingPsd(true);
    setTextActionError(null);

    try {
      await exportPageAsPsd({
        originalImageSrc: resolveApiAssetUrl(currentPage.original_asset_path),
        workingImageSrc: resolveApiAssetUrl(getPreferredExportAssetPath(currentPage)),
        fileName: buildPsdExportFileName(currentPage.file_name),
        width: currentPage.width,
        height: currentPage.height,
        entries: textPreviewEntries,
      });
    } catch (error) {
      setTextActionError(getErrorMessage(error, messages.editor.exportPsdErrorFallback));
    } finally {
      setIsExportingPsd(false);
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
                {orderedRegions.map((region, index) => {
                  const isSelected = region.id === selectedRegionId;
                  return (
                    <article className={getRegionCardClassName(region, isSelected)} key={region.id}>
                      <div className="editor-region-card-header">
                        <span className="card-step">
                          {regionDisplayLabels.get(region.id) ?? `R${String(index + 1).padStart(2, "0")}`}
                        </span>
                        <span className="editor-region-state-pill">
                          {messages.editor.regionStateLabels[region.state]}
                        </span>
                      </div>
                      <strong>{messages.editor.regionTypeLabels[region.type]}</strong>
                      <p className="card-description">{formatRegionBounds(region)}</p>
                      <button
                        className={isSelected ? "secondary-button" : "ghost-button"}
                        onClick={() => handleSelectRegion(region.id, "context_area")}
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
                  <span className="status-item-label">{messages.editor.regionReadingOrderLabel}</span>
                  <strong>
                    {selectedRegionDisplayLabel ?? messages.editor.regionOrderUnknown}
                  </strong>
                </div>
                <p className="card-description">{messages.editor.readingOrderHint}</p>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionPanelOrderLabel}</span>
                  <strong>{selectedRegion.panel_order ?? messages.editor.regionOrderUnknown}</strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionBalloonGroupOrderLabel}</span>
                  <strong>
                    {selectedRegion.balloon_group_order ?? messages.editor.regionOrderUnknown}
                  </strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionOrderInBalloonGroupLabel}</span>
                  <strong>
                    {selectedRegion.order_in_balloon_group ?? messages.editor.regionOrderUnknown}
                  </strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.regionOrderInPanelLabel}</span>
                  <strong>
                    {selectedRegion.order_in_panel ?? messages.editor.regionOrderUnknown}
                  </strong>
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
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.cleanupStrategyLabel}</span>
                  <strong>
                    {selectedRegion.cleanup_strategy === null
                      ? messages.editor.cleanupStrategyUnknown
                      : selectedRegion.cleanup_confidence === null
                        ? messages.editor.cleanupStrategyLabels[selectedRegion.cleanup_strategy]
                        : `${messages.editor.cleanupStrategyLabels[selectedRegion.cleanup_strategy]} (${Math.round(selectedRegion.cleanup_confidence * 100)}%)`}
                  </strong>
                </div>
                <div className="editor-selection-meta">
                  <span className="status-item-label">{messages.editor.editingAreaLabel}</span>
                  <strong>{messages.editor.areaKindLabels[selectedRegionArea]}</strong>
                </div>
                <p className="card-description">
                  {messages.editor.areaPurposeHints[selectedRegionArea]}
                </p>

                <div className="editor-selection-actions">
                  <button
                    className="ghost-button"
                    disabled={
                      updatingRegionId === selectedRegion.id
                      || hasRunningJobsForPage
                      || selectedRegionOrderIndex <= 0
                    }
                    onClick={() => void handleMoveSelectedRegionReadingOrder(-1)}
                    type="button"
                  >
                    {messages.editor.moveEarlierAction}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={
                      updatingRegionId === selectedRegion.id
                      || hasRunningJobsForPage
                      || selectedRegionOrderIndex === -1
                      || selectedRegionOrderIndex >= orderedRegions.length - 1
                    }
                    onClick={() => void handleMoveSelectedRegionReadingOrder(1)}
                    type="button"
                  >
                    {messages.editor.moveLaterAction}
                  </button>
                  <button
                    className={
                      selectedRegionArea === "context_area" ? "secondary-button" : "ghost-button"
                    }
                    onClick={() => setSelectedRegionArea("context_area")}
                    type="button"
                  >
                    {messages.editor.areaKindLabels.context_area}
                  </button>
                  <button
                    className={
                      selectedRegionArea === "text_area" ? "secondary-button" : "ghost-button"
                    }
                    onClick={() => setSelectedRegionArea("text_area")}
                    type="button"
                  >
                    {messages.editor.areaKindLabels.text_area}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={
                      isRefiningTextArea
                      || updatingRegionId === selectedRegion.id
                      || hasRunningJobsForPage
                    }
                    onClick={() => void handleRefineSelectedTextArea()}
                    type="button"
                  >
                    {isRefiningTextArea
                      ? messages.editor.refiningTextAreaAction
                      : messages.editor.refineTextAreaAction}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={updatingRegionId === selectedRegion.id || hasRunningJobsForPage}
                    onClick={() => void handleUpdateRegionState("reviewed")}
                    type="button"
                  >
                    {messages.editor.markReviewedAction}
                  </button>
                  <button
                    className="secondary-button"
                    disabled={updatingRegionId === selectedRegion.id || hasRunningJobsForPage}
                    onClick={() => void handleUpdateRegionState("approved")}
                    type="button"
                  >
                    {messages.editor.approveRegionAction}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={updatingRegionId === selectedRegion.id || hasRunningJobsForPage}
                    onClick={() => void handleUpdateRegionState("draft")}
                    type="button"
                  >
                    {messages.editor.resetRegionAction}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={deletingRegionId === selectedRegion.id || hasRunningJobsForPage}
                    onClick={() => void handleDeleteSelectedRegion()}
                    type="button"
                  >
                    {deletingRegionId === selectedRegion.id
                      ? messages.editor.deletingRegionAction
                      : messages.editor.deleteRegionAction}
                  </button>
                </div>

                <div className="editor-selection-adjustments">
                  <span className="status-item-label">{messages.editor.adjustBoundsLabel}</span>
                  <p className="card-description">{messages.editor.dragResizeHint}</p>
                  <div className="editor-adjustment-group">
                    <button
                      className="ghost-button"
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          moveBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegionAreaBoundingBox,
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
                      disabled={
                        updatingRegionId === selectedRegion.id || selectedRegionAreaBoundingBox === null
                      }
                      onClick={() =>
                        selectedRegionAreaBoundingBox === null
                          ? undefined
                          : void handleUpdateSelectedRegionBoundingBox(
                          resizeBoundingBox(
                            selectedRegionAreaBoundingBox,
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
            {hasRunningJobsForPage ? (
              <p className="notice notice-warning">{messages.editor.runningJobsNotice}</p>
            ) : null}
            {!hasRunningJobsForPage && hasQueuedJobsForPage ? (
              <p className="notice notice-warning">{messages.editor.queuedJobsNotice}</p>
            ) : null}

            <p className="card-description">
              {messages.editor.approvedMasksSummary.replace(
                "{count}",
                String(approvedActiveMaskRevisionCount),
              )}
            </p>
            <p className="card-description">
              {messages.editor.ocrCandidatesSummary.replace(
                "{count}",
                String(ocrCandidateRegionCount),
              )}
            </p>
            <p className="card-description">
              {messages.editor.unassignedDialoguesSummary.replace(
                "{count}",
                String(unassignedDialogueCount),
              )}
            </p>

            <div className="editor-selection-actions">
              <button
                className="primary-button"
                disabled={isQueueingDetection || hasPendingDetectionJob}
                onClick={() => void handleQueueRegionDetection()}
                type="button"
              >
                {isQueueingDetection
                  ? messages.editor.queuingDetectionAction
                  : messages.editor.queueDetectionAction}
              </button>
              <button
                className="ghost-button"
                disabled={isResettingRegions || regions.length === 0 || hasRunningJobsForPage}
                onClick={() => void handleResetRegions()}
                type="button"
              >
                {isResettingRegions
                  ? messages.editor.resettingRegionsAction
                  : messages.editor.resetRegionsAction}
              </button>
              <button
                className="secondary-button"
                disabled={
                  isQueueingCleanup
                  || hasPendingCleanupJob
                  || getCleanupMaskCandidateRegions(regions).length === 0
                }
                onClick={() => void handleQueueCleanup()}
                type="button"
              >
                {isQueueingCleanup
                  ? messages.editor.queuingCleanupAction
                  : messages.editor.queueCleanupAction}
              </button>
            </div>

            <div className="editor-selection-actions">
              <button
                className="secondary-button"
                disabled={isQueueingOcr || hasPendingOcrJob || ocrCandidateRegionCount === 0}
                onClick={() => void handleQueueOcr()}
                type="button"
              >
                {isQueueingOcr
                  ? messages.editor.queuingOcrAction
                  : messages.editor.queueOcrAction}
              </button>
              <button
                className="ghost-button"
                disabled={isQueueingTranslation || hasPendingTranslationJob || dialogues.length === 0}
                onClick={() => void handleQueueAutomaticTranslation()}
                type="button"
              >
                {isQueueingTranslation
                  ? messages.editor.queuingTranslationAction
                  : messages.editor.queueTranslationAction}
              </button>
              <button
                className="ghost-button"
                disabled={
                  isQueueingMatching
                  || hasPendingMatchingJob
                  || unassignedDialogueCount === 0
                  || availableMatchingRegionCount === 0
                }
                onClick={() => void handleQueueDialogueMatching()}
                type="button"
              >
                {isQueueingMatching
                  ? messages.editor.queuingMatchingAction
                  : messages.editor.queueMatchingAction}
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

            <div className="section-head section-head-compact">
              <h2 className="section-title">{messages.editor.textSectionTitle}</h2>
              <p className="section-copy">{messages.editor.textSectionCopy}</p>
            </div>

            {textLoadError ? <p className="notice notice-error">{textLoadError}</p> : null}
            {textActionError ? <p className="notice notice-error">{textActionError}</p> : null}

            <div className="editor-selection-actions">
              <button
                className="ghost-button"
                onClick={handleStartNewDialogue}
                type="button"
              >
                {messages.editor.newDialogueAction}
              </button>
            </div>

            {isTextLoading ? (
              <p className="empty-state">{messages.editor.textLoading}</p>
            ) : dialogues.length === 0 ? (
              <p className="empty-state">{messages.editor.dialoguesEmpty}</p>
            ) : (
              <div className="editor-region-list">
                {dialogues.map((dialogue) => {
                  const translation =
                    translations.find((candidate) => candidate.dialogue_id === dialogue.id) ?? null;
                  const assignment =
                    assignments.find((candidate) => candidate.dialogue_id === dialogue.id) ?? null;
                  const isSelected = dialogue.id === selectedDialogueId;
                  return (
                    <article
                      className={isSelected ? "editor-region-card editor-region-card-selected" : "editor-region-card"}
                      key={dialogue.id}
                    >
                      <div className="editor-region-card-header">
                        <span className="card-step">
                          {messages.editor.dialogueOrderLabel.replace(
                            "{order}",
                            String(dialogue.reading_order),
                          )}
                        </span>
                        <span className="editor-region-state-pill">
                          {assignment
                            ? messages.editor.dialogueAssignedValue
                            : messages.editor.dialogueUnassignedValue}
                        </span>
                      </div>
                      <strong>{dialogue.content}</strong>
                      <p className="card-description">
                        {translation?.content || messages.editor.translationEmptyValue}
                      </p>
                      <button
                        className={isSelected ? "secondary-button" : "ghost-button"}
                        onClick={() => setSelectedDialogueId(dialogue.id)}
                        type="button"
                      >
                        {isSelected
                          ? messages.editor.selectedDialogueAction
                          : messages.editor.selectDialogueAction}
                      </button>
                    </article>
                  );
                })}
              </div>
            )}

            <div className="editor-selection-panel">
              <div className="editor-selection-meta">
                <span className="status-item-label">{messages.editor.dialogueEditingLabel}</span>
                <strong>
                  {selectedDialogue
                    ? messages.editor.editingDialogueValue.replace(
                        "{order}",
                        String(selectedDialogue.reading_order),
                      )
                    : messages.editor.newDialogueValue}
                </strong>
              </div>
              <label className="field-label" htmlFor="dialogue-source">
                {messages.editor.sourceTextLabel}
              </label>
              <textarea
                className="field-input editor-textarea"
                id="dialogue-source"
                onChange={(event) => setDialogueDraft(event.target.value)}
                rows={4}
                value={dialogueDraft}
              />
              <label className="field-label" htmlFor="dialogue-translation">
                {messages.editor.translationTextLabel}
              </label>
              <textarea
                className="field-input editor-textarea"
                id="dialogue-translation"
                onChange={(event) => setTranslationDraft(event.target.value)}
                rows={4}
                value={translationDraft}
              />
              <p className="card-description">
                {selectedRegion
                  ? messages.editor.dialogueRegionHint.replace(
                      "{region}",
                      messages.editor.regionTypeLabels[selectedRegion.type],
                    )
                  : messages.editor.dialogueRegionMissingHint}
              </p>
              {selectedDialoguePlacement ? (
                <div className="editor-selection-adjustments">
                  <span className="status-item-label">{messages.editor.adjustTextBoxLabel}</span>
                  <div className="editor-adjustment-group">
                    <button
                      className="ghost-button"
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          moveBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          moveBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          moveBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          moveBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          resizeBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          resizeBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          resizeBoundingBox(
                            selectedDialoguePlacement.text_box,
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
                      disabled={updatingPlacementId === selectedDialoguePlacement.id}
                      onClick={() =>
                        void handleUpdatePlacementBoundingBox(
                          resizeBoundingBox(
                            selectedDialoguePlacement.text_box,
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
              ) : null}
              <button
                className="primary-button"
                disabled={isSavingDialogue}
                onClick={() => void handleSaveDialogueWorkflow()}
                type="button"
              >
                {isSavingDialogue
                  ? messages.editor.savingDialogueAction
                  : selectedDialogue
                    ? messages.editor.updateDialogueAction
                    : messages.editor.createDialogueAction}
              </button>
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
                <button
                  className="secondary-button"
                  onClick={() => setShowContextAreas((currentValue) => !currentValue)}
                  type="button"
                >
                  {showContextAreas
                    ? messages.editor.hideContextAreasAction
                    : messages.editor.showContextAreasAction}
                </button>
                <button
                  className="ghost-button"
                  onClick={() => setShowTextAreas((currentValue) => !currentValue)}
                  type="button"
                >
                  {showTextAreas
                    ? messages.editor.hideTextAreasAction
                    : messages.editor.showTextAreasAction}
                </button>
                <button
                  className="ghost-button"
                  onClick={() => setShowBalloonGroups((currentValue) => !currentValue)}
                  type="button"
                >
                  {showBalloonGroups
                    ? messages.editor.hideBalloonGroupsAction
                    : messages.editor.showBalloonGroupsAction}
                </button>
                <button
                  className="ghost-button"
                  onClick={() => setShowOverlayLabels((currentValue) => !currentValue)}
                  type="button"
                >
                  {showOverlayLabels
                    ? messages.editor.hideOverlayLabelsAction
                    : messages.editor.showOverlayLabelsAction}
                </button>
                <button
                  className="ghost-button"
                  onClick={() => setShowPanelAreas((currentValue) => !currentValue)}
                  type="button"
                >
                  {showPanelAreas
                    ? messages.editor.hidePanelAreasAction
                    : messages.editor.showPanelAreasAction}
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
                <button
                  className="ghost-button"
                  disabled={isExportingJpeg}
                  onClick={() => void handleExportCurrentPageJpeg()}
                  type="button"
                >
                  {isExportingJpeg
                    ? messages.editor.exportingJpegAction
                    : messages.editor.exportJpegAction}
                </button>
                <button
                  className="ghost-button"
                  disabled={isExportingPdf}
                  onClick={() => void handleExportCurrentPagePdf()}
                  type="button"
                >
                  {isExportingPdf
                    ? messages.editor.exportingPdfAction
                    : messages.editor.exportPdfAction}
                </button>
                <button
                  className="ghost-button"
                  disabled={isExportingPsd}
                  onClick={() => void handleExportCurrentPagePsd()}
                  type="button"
                >
                  {isExportingPsd
                    ? messages.editor.exportingPsdAction
                    : messages.editor.exportPsdAction}
                </button>
              </div>
            </div>

            {currentCanvasSize?.usedFallback ? (
              <p className="notice notice-warning">{messages.editor.dimensionsFallbackNotice}</p>
            ) : null}

            <div className="editor-canvas-frame">
              <div
                className="editor-page-stage"
                ref={stageRef}
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

                {showPanelAreas
                  ? panelOverlays.map((overlay, index) => {
                      const isSelected = selectedRegion?.panel_order === overlay.order;
                      return (
                        <div
                          className={`editor-structure-overlay editor-structure-overlay-panel${
                            isSelected ? " editor-structure-overlay-selected" : ""
                          }`}
                          key={overlay.id}
                          style={getBoundingBoxOverlayStyle(overlay.bounding_box, currentPage)}
                        >
                          {showOverlayLabels ? (
                            <>
                              <span className="editor-structure-chip">
                                {formatPanelOverlayLabel(overlay, index)}
                              </span>
                              <span className="editor-structure-caption">
                                {messages.editor.panelAreaLabel}
                              </span>
                            </>
                          ) : null}
                        </div>
                      );
                    })
                  : null}

                {showBalloonGroups
                  ? balloonGroupOverlays.map((overlay, index) => {
                      const isSelected =
                        selectedRegion?.balloon_group_id !== null
                        && selectedRegion?.balloon_group_id !== undefined
                        ? selectedRegion.balloon_group_id === overlay.id
                        : selectedRegion?.balloon_group_order === overlay.order;
                      return (
                        <div
                          className={`editor-structure-overlay editor-structure-overlay-balloon-group${
                            isSelected ? " editor-structure-overlay-selected" : ""
                          }`}
                          key={overlay.id}
                          style={getBoundingBoxOverlayStyle(overlay.bounding_box, currentPage)}
                        >
                          {showOverlayLabels ? (
                            <>
                              <span className="editor-structure-chip">
                                {formatBalloonGroupOverlayLabel(overlay, index)}
                              </span>
                              <span className="editor-structure-caption">
                                {messages.editor.balloonGroupLabel}
                              </span>
                            </>
                          ) : null}
                        </div>
                      );
                    })
                  : null}

                {showContextAreas
                  ? orderedRegions.map((region, index) => {
                      const isSelected = region.id === selectedRegionId;
                      const isActiveArea = isSelected && selectedRegionArea === "context_area";
                      return (
                        <button
                          aria-pressed={isSelected}
                          className={getRegionOverlayClassName(
                            region,
                            "context_area",
                            isSelected,
                            isActiveArea,
                          )}
                          key={region.id}
                          onClick={() => handleSelectRegion(region.id, "context_area")}
                          onMouseDown={(event) =>
                            handleRegionAreaMouseDown(event, region, "context_area")
                          }
                          style={getBoundingBoxOverlayStyle(
                            getRegionAreaDisplayBoundingBox(region, "context_area"),
                            currentPage,
                          )}
                          type="button"
                        >
                          {showOverlayLabels ? (
                            <>
                              <span className="editor-region-chip">
                                {regionDisplayLabels.get(region.id) ?? `R${String(index + 1).padStart(2, "0")}`}
                              </span>
                              <span className="editor-region-caption">
                                {messages.editor.regionTypeLabels[region.type]}
                              </span>
                            </>
                          ) : null}
                        </button>
                      );
                    })
                  : null}

                {showTextAreas
                  ? orderedRegions.map((region, index) => {
                      const isSelected = region.id === selectedRegionId;
                      const isActiveArea = isSelected && selectedRegionArea === "text_area";
                      return (
                        <button
                          aria-pressed={isSelected}
                          className={getRegionOverlayClassName(
                            region,
                            "text_area",
                            isSelected,
                            isActiveArea,
                          )}
                          key={`${region.id}-text`}
                          onClick={() => handleSelectRegion(region.id, "text_area")}
                          onMouseDown={(event) =>
                            handleRegionAreaMouseDown(event, region, "text_area")
                          }
                          style={getBoundingBoxOverlayStyle(
                            getRegionAreaDisplayBoundingBox(region, "text_area"),
                            currentPage,
                          )}
                          type="button"
                        >
                          {showOverlayLabels ? (
                            <>
                              <span className="editor-region-chip">
                                {regionDisplayLabels.get(region.id) ?? `R${String(index + 1).padStart(2, "0")}`}
                              </span>
                              <span className="editor-region-caption">
                                {messages.editor.areaKindLabels.text_area}
                              </span>
                            </>
                          ) : null}
                        </button>
                      );
                    })
                  : null}

                {(selectedRegionArea === "context_area" ? showContextAreas : showTextAreas)
                  && selectedRegion !== null
                  && selectedRegionAreaBoundingBox !== null ? (
                  <div
                    className="editor-region-handle-layer"
                    style={getBoundingBoxOverlayStyle(selectedRegionAreaBoundingBox, currentPage)}
                  >
                    {(["nw", "ne", "sw", "se"] as const).map((handle) => (
                      <button
                        className={`editor-region-handle editor-region-handle-${handle}`}
                        key={handle}
                        onMouseDown={(event) =>
                          handleRegionResizeHandleMouseDown(
                            event,
                            selectedRegion,
                            selectedRegionArea,
                            handle,
                          )
                        }
                        type="button"
                      />
                    ))}
                  </div>
                ) : null}

                {textPreviewEntries.map((entry) => (
                  <div
                    className="editor-text-overlay"
                    key={entry.id}
                    style={getPlacementOverlayStyle(entry.placement, currentPage)}
                  >
                    <span>{entry.text}</span>
                  </div>
                ))}
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
