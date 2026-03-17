type StatusItem = {
  label: string;
  value: string;
  description: string;
};

type TimelineItem = {
  step: string;
  title: string;
  description: string;
};

type LanguageOption = {
  value: string;
  label: string;
};

type RegionTypeLabels = {
  speech_balloon: string;
  narration_box: string;
  free_text: string;
  sfx: string;
  unknown: string;
};

type RegionStateLabels = {
  draft: string;
  reviewed: string;
  approved: string;
  rejected: string;
};

type RegionOriginLabels = {
  detected: string;
  user_created: string;
  user_split: string;
  user_merged: string;
};

type CleanupStrategyLabels = {
  solid_fill: string;
  background_reconstruction: string;
};

type JobTypeLabels = {
  detect_regions: string;
  generate_cleanup: string;
  run_ocr: string;
  generate_translation: string;
  match_dialogue: string;
  generate_typesetting: string;
  export_project: string;
};

type JobStatusLabels = {
  queued: string;
  running: string;
  succeeded: string;
  failed: string;
  canceled: string;
};

export type AppMessages = {
  common: {
    appName: string;
    brandNote: string;
    localeSwitcherLabel: string;
  };
  home: {
    eyebrow: string;
    title: string;
    subtitle: string;
    primaryAction: string;
    secondaryAction: string;
    foundationTitle: string;
    foundationCopy: string;
    foundationItems: ReadonlyArray<StatusItem>;
    workflowTitle: string;
    workflowCopy: string;
    workflowItems: ReadonlyArray<TimelineItem>;
    deliveryTitle: string;
    deliveryCopy: string;
    deliveryItems: ReadonlyArray<TimelineItem>;
    milestoneNote: string;
    defaultWorkspaceLabel: string;
  };
  dashboard: {
    kicker: string;
    apiLoading: string;
    apiOnline: string;
    apiOffline: string;
    loadErrorFallback: string;
    createErrorFallback: string;
    uploadErrorFallback: string;
    uploadSuccess: string;
    projectTitle: string;
    projectCopy: string;
    projectNameLabel: string;
    projectNamePlaceholder: string;
    sourceLanguageLabel: string;
    targetLanguageLabel: string;
    sourceLanguageOptions: ReadonlyArray<LanguageOption>;
    targetLanguageOptions: ReadonlyArray<LanguageOption>;
    createAction: string;
    creatingAction: string;
    projectListTitle: string;
    projectListCopy: string;
    projectListEmpty: string;
    openProjectAction: string;
    pageCountLabel: string;
    uploadTitle: string;
    uploadCopy: string;
    selectedProjectLabel: string;
    noProjectSelected: string;
    chooseFilesAction: string;
    uploadQueueEmpty: string;
    dimensionsPending: string;
    removeAction: string;
    registerAction: string;
    registeringAction: string;
    uploadHint: string;
    pagesLoading: string;
    pagesTitle: string;
    pagesCopy: string;
    pagesEmpty: string;
    pageIndexLabel: string;
    storedOriginalLabel: string;
    rejectionReasons: {
      unsupported_type: string;
      too_large: string;
      duplicate_name: string;
    };
  };
  workspace: {
    kicker: string;
    backToDashboard: string;
    loadErrorFallback: string;
    loadingProject: string;
    loadingProjectTitle: string;
    heroCopy: string;
    sourceLanguageLabel: string;
    targetLanguageLabel: string;
    pageCountLabel: string;
    statusLabel: string;
    summaryTitle: string;
    summaryCopy: string;
    summaryItems: ReadonlyArray<StatusItem>;
    pagesTitle: string;
    pagesCopy: string;
    pageLabel: string;
    emptyPages: string;
    stayInProjectAction: string;
    openEditorAction: string;
  };
  editor: {
    backToProject: string;
    loadErrorFallback: string;
    regionLoadErrorFallback: string;
    regionCreateErrorFallback: string;
    regionUpdateErrorFallback: string;
    regionDeleteErrorFallback: string;
    regionResetErrorFallback: string;
    maskLoadErrorFallback: string;
    maskCreateErrorFallback: string;
    maskUpdateErrorFallback: string;
    loadingEditor: string;
    pageNotFound: string;
    pageNavigatorTitle: string;
    pageNavigatorCopy: string;
    pageLabel: string;
    sidebarTitle: string;
    sidebarCopy: string;
    regionsLoading: string;
    regionsEmpty: string;
    selectRegionAction: string;
    selectedRegionAction: string;
    selectionTitle: string;
    selectionCopy: string;
    selectionEmpty: string;
    regionTypeLabel: string;
    regionStateLabel: string;
    regionOriginLabel: string;
    regionBoundsLabel: string;
    regionConfidenceLabel: string;
    regionConfidenceUnknown: string;
    cleanupStrategyLabel: string;
    cleanupStrategyUnknown: string;
    cleanupStrategyLabels: CleanupStrategyLabels;
    maskSectionTitle: string;
    maskSectionCopy: string;
    masksLoading: string;
    masksEmptyForRegion: string;
    maskVersionLabel: string;
    maskVersionValue: string;
    maskApprovalLabel: string;
    maskApprovedValue: string;
    maskPendingValue: string;
    maskPointsLabel: string;
    createMaskFromRegionAction: string;
    refreshMaskFromRegionAction: string;
    creatingMaskAction: string;
    approveMaskAction: string;
    approvingMaskAction: string;
    regionTypeLabels: RegionTypeLabels;
    regionStateLabels: RegionStateLabels;
    regionOriginLabels: RegionOriginLabels;
    adjustBoundsLabel: string;
    moveLeftAction: string;
    moveUpAction: string;
    moveDownAction: string;
    moveRightAction: string;
    narrowerAction: string;
    widerAction: string;
    shorterAction: string;
    tallerAction: string;
    jobsTitle: string;
    jobsCopy: string;
    jobsLoading: string;
    jobsEmpty: string;
    jobLoadErrorFallback: string;
    jobCreateErrorFallback: string;
    queuedJobsNotice: string;
    runningJobsNotice: string;
    textLoadErrorFallback: string;
    textSaveErrorFallback: string;
    approvedMasksSummary: string;
    ocrCandidatesSummary: string;
    unassignedDialoguesSummary: string;
    queueDetectionAction: string;
    queuingDetectionAction: string;
    queueCleanupAction: string;
    queuingCleanupAction: string;
    queueOcrAction: string;
    queuingOcrAction: string;
    queueTranslationAction: string;
    queuingTranslationAction: string;
    queueMatchingAction: string;
    queuingMatchingAction: string;
    jobTypeLabels: JobTypeLabels;
    jobStatusLabels: JobStatusLabels;
    kicker: string;
    canvasCopy: string;
    showRegionsAction: string;
    hideRegionsAction: string;
    addRegionAction: string;
    creatingRegionAction: string;
    markReviewedAction: string;
    approveRegionAction: string;
    resetRegionAction: string;
    deleteRegionAction: string;
    deletingRegionAction: string;
    resetRegionsAction: string;
    resettingRegionsAction: string;
    textSectionTitle: string;
    textSectionCopy: string;
    textLoading: string;
    dialoguesEmpty: string;
    dialogueOrderLabel: string;
    dialogueAssignedValue: string;
    dialogueUnassignedValue: string;
    translationEmptyValue: string;
    selectDialogueAction: string;
    selectedDialogueAction: string;
    dialogueEditingLabel: string;
    editingDialogueValue: string;
    newDialogueValue: string;
    sourceTextLabel: string;
    translationTextLabel: string;
    dialogueRegionHint: string;
    dialogueRegionMissingHint: string;
    sourceTextRequired: string;
    createDialogueAction: string;
    updateDialogueAction: string;
    savingDialogueAction: string;
    newDialogueAction: string;
    adjustTextBoxLabel: string;
    exportJpegAction: string;
    exportingJpegAction: string;
    exportJpegErrorFallback: string;
    exportPdfAction: string;
    exportingPdfAction: string;
    exportPdfErrorFallback: string;
    exportPsdAction: string;
    exportingPsdAction: string;
    exportPsdErrorFallback: string;
    overlayRegionCount: string;
    canvasEmptyState: string;
    dimensionsFallbackNotice: string;
    cleanupPreviewTitle: string;
    cleanupPreviewCopy: string;
    cleanupPreviewEmpty: string;
    originalPreviewLabel: string;
    cleanedPreviewLabel: string;
  };
};

export const enUSMessages: AppMessages = {
  common: {
    appName: "MangAI",
    brandNote: "AI-first localization workspace for manga and comics.",
    localeSwitcherLabel: "Interface language",
  },
  home: {
    eyebrow: "AI-first localization pipeline",
    title: "Clean, translate, and typeset pages with human control.",
    subtitle:
      "MangAI keeps every step editable, from region review and cleanup masks to dialogue matching and PSD-ready exports.",
    primaryAction: "Review workflow",
    secondaryAction: "Inspect foundation",
    foundationTitle: "Current foundation",
    foundationCopy:
      "The monorepo already has shared contracts, a tested API base, and locale-aware frontend primitives wired for English and Portuguese.",
    foundationItems: [
      {
        label: "Shared schema",
        value: "Ready",
        description: "Project entities, locale rules, and job contracts live in a single TypeScript package.",
      },
      {
        label: "API baseline",
        value: "Tested",
        description: "FastAPI routes, settings, and request validation are already covered by automated tests.",
      },
      {
        label: "UI locales",
        value: "Enabled",
        description: "The interface now resolves supported locales, serves typed catalogs, and rejects unsupported ones safely.",
      },
    ],
    workflowTitle: "Execution path",
    workflowCopy:
      "The first product slice stays aligned with the architecture plan: establish the shell, lock the contracts, then add workflows one capability at a time.",
    workflowItems: [
      {
        step: "01",
        title: "Upload and inspect",
        description:
          "Create a project, ingest pages, and expose every detected asset as a first-class object with explicit lifecycle states.",
      },
      {
        step: "02",
        title: "Clean the art",
        description:
          "Review masks, compare cleanup variants, and keep the original art accessible for precise Photoshop finishing.",
      },
      {
        step: "03",
        title: "Translate and map dialogue",
        description:
          "Import a script or OCR text, match each line to the correct region, and keep the review loop fast and auditable.",
      },
      {
        step: "04",
        title: "Typeset and export",
        description:
          "Place text with style presets, preserve editability, and deliver PSD, JPG, and PDF outputs from a single project state.",
      },
    ],
    deliveryTitle: "Why this slice matters",
    deliveryCopy:
      "This frontend foundation is intentionally narrow: it proves routing, i18n, shared contracts, and build reliability before heavier editor interactions land.",
    deliveryItems: [
      {
        step: "A",
        title: "Predictable locale handling",
        description: "Every supported locale is explicit, typed, and validated against the shared contract package.",
      },
      {
        step: "B",
        title: "Buildable Next.js shell",
        description: "The web app now boots as a real App Router project instead of a placeholder workspace directory.",
      },
      {
        step: "C",
        title: "Test-first progress",
        description: "Frontend helpers are verified with automated tests, and the web app build itself is part of validation.",
      },
      {
        step: "D",
        title: "Safer next steps",
        description: "The next feature slices can focus on dashboard data, uploads, and editor interactions without rewriting the base.",
      },
    ],
    milestoneNote:
      "Current milestone: web shell online, locales active, contracts shared, and automated validation in place.",
    defaultWorkspaceLabel: "Default workspace locale",
  },
  dashboard: {
    kicker: "Project setup and upload",
    apiLoading: "Connecting",
    apiOnline: "API online",
    apiOffline: "API offline",
    loadErrorFallback: "The workspace could not load projects from the API.",
    createErrorFallback: "The project could not be created right now.",
    uploadErrorFallback: "The selected pages could not be registered right now.",
    uploadSuccess: "{count} pages registered successfully.",
    projectTitle: "Create a project and establish its translation direction.",
    projectCopy:
      "This slice already talks to the API. You can create draft projects, inspect existing ones, and send a first upload batch that persists both page records and original files.",
    projectNameLabel: "Project name",
    projectNamePlaceholder: "Chapter 01 - Review pass",
    sourceLanguageLabel: "Source language",
    targetLanguageLabel: "Target language",
    sourceLanguageOptions: [
      { value: "ja-JP", label: "Japanese" },
      { value: "ko-KR", label: "Korean" },
      { value: "zh-CN", label: "Chinese" },
      { value: "en-US", label: "English" },
    ],
    targetLanguageOptions: [
      { value: "pt-BR", label: "Portuguese" },
      { value: "en-US", label: "English" },
    ],
    createAction: "Create project",
    creatingAction: "Creating project...",
    projectListTitle: "Current project board",
    projectListCopy:
      "Each card reflects the API state. Select one project to become the active destination for the upload queue.",
    projectListEmpty: "No projects yet. Create the first one to unlock the upload queue.",
    openProjectAction: "Open project workspace",
    pageCountLabel: "{count} registered pages",
    uploadTitle: "Prepare the first upload batch",
    uploadCopy:
      "Pick page files from your machine, review the queue, and upload them into the selected project. The API now persists both metadata and the original binary asset locally.",
    selectedProjectLabel: "Active project",
    noProjectSelected: "Select or create a project first",
    chooseFilesAction: "Choose page files",
    uploadQueueEmpty: "No pages in the queue yet. Add JPEG, PNG, or WEBP files to continue.",
    dimensionsPending: "dimensions captured later",
    removeAction: "Remove",
    registerAction: "Register pages",
    registeringAction: "Registering pages...",
    uploadHint:
      "Each upload stores the original file locally, persists the page record, and increments the project page count.",
    pagesLoading: "Loading project pages...",
    pagesTitle: "Stored project pages",
    pagesCopy:
      "These pages come from the persisted API state. They survive server restarts and point to the original uploaded asset.",
    pagesEmpty: "This project still has no stored pages.",
    pageIndexLabel: "Page {index}",
    storedOriginalLabel: "Original asset stored locally",
    rejectionReasons: {
      unsupported_type: "{file}: unsupported file type. Use JPEG, PNG, or WEBP.",
      too_large: "{file}: file exceeds the current 25 MB limit.",
      duplicate_name: "{file}: duplicate file name detected in this queue.",
    },
  },
  workspace: {
    kicker: "Project workspace",
    backToDashboard: "Back to dashboard",
    loadErrorFallback: "The selected project could not be loaded.",
    loadingProject: "Loading project workspace...",
    loadingProjectTitle: "Preparing workspace...",
    heroCopy:
      "This workspace is the bridge between project setup and the visual editor. It gives us a durable place for page review, job status, and navigation before the heavier tooling lands.",
    sourceLanguageLabel: "Source language",
    targetLanguageLabel: "Target language",
    pageCountLabel: "Registered pages",
    statusLabel: "Project status",
    summaryTitle: "Why this page exists",
    summaryCopy:
      "The goal of this slice is to anchor the user inside one project and make page-by-page work feel tangible instead of abstract.",
    summaryItems: [
      {
        label: "Navigation",
        value: "Active",
        description: "Projects now have a stable URL and a clear jump point into page-level work.",
      },
      {
        label: "Persistence",
        value: "Ready",
        description: "Every page shown here comes from the persisted local API store and survives app restarts.",
      },
      {
        label: "Editor path",
        value: "Primed",
        description: "Each uploaded page can already open an editor shell where cleanup and typesetting tools will land next.",
      },
    ],
    pagesTitle: "Page board",
    pagesCopy:
      "Open any page to enter the editor shell. This is where region review, cleanup masks, dialogue mapping, and typesetting controls will start to converge.",
    pageLabel: "Page {index}",
    emptyPages: "This project has no pages yet. Return to the dashboard and upload the first batch.",
    stayInProjectAction: "Project overview",
    openEditorAction: "Open editor shell",
  },
  editor: {
    backToProject: "Back to project",
    loadErrorFallback: "The editor could not load the selected project page.",
    regionLoadErrorFallback: "The editor could not load the saved review regions for this page.",
    regionCreateErrorFallback: "The editor could not create a new review region right now.",
    regionUpdateErrorFallback: "The editor could not update the selected region right now.",
    regionDeleteErrorFallback: "The editor could not delete the selected region right now.",
    regionResetErrorFallback: "The editor could not reset the saved regions for this page right now.",
    maskLoadErrorFallback: "The editor could not load the saved cleanup masks for this page.",
    maskCreateErrorFallback: "The editor could not create a cleanup mask right now.",
    maskUpdateErrorFallback: "The editor could not update the selected cleanup mask right now.",
    loadingEditor: "Loading editor shell...",
    pageNotFound: "This page could not be found in the selected project.",
    pageNavigatorTitle: "Page navigator",
    pageNavigatorCopy:
      "Switch between uploaded pages without losing the editor context. This is the first step toward chapter-scale review.",
    pageLabel: "Page {index}",
    sidebarTitle: "Region review",
    sidebarCopy:
      "This first review layer persists page regions, lets you select them, and gives the editor a concrete surface for the next cleanup and dialogue tools.",
    regionsLoading: "Loading saved regions...",
    regionsEmpty: "No regions exist yet for this page. Add the first one to begin the review pass.",
    selectRegionAction: "Select region",
    selectedRegionAction: "Selected",
    selectionTitle: "Selected region",
    selectionCopy:
      "Keep the review loop lightweight: inspect one region, confirm its state, then move to the next without leaving the page.",
    selectionEmpty: "Select a region from the list or create a new one from the canvas toolbar.",
    regionTypeLabel: "Type",
    regionStateLabel: "State",
    regionOriginLabel: "Origin",
    regionBoundsLabel: "Bounds",
    regionConfidenceLabel: "Confidence",
    regionConfidenceUnknown: "Manual",
    cleanupStrategyLabel: "Suggested cleanup",
    cleanupStrategyUnknown: "Needs review",
    cleanupStrategyLabels: {
      solid_fill: "Simple fill",
      background_reconstruction: "Reconstruct background",
    },
    maskSectionTitle: "Cleanup mask",
    maskSectionCopy:
      "Each active mask revision becomes the cleanup source of truth for this region. Create a new version from the reviewed region and approve it before queuing cleanup.",
    masksLoading: "Loading cleanup masks...",
    masksEmptyForRegion: "No cleanup mask exists for this region yet.",
    maskVersionLabel: "Active version",
    maskVersionValue: "Mask v{version}",
    maskApprovalLabel: "Approval",
    maskApprovedValue: "Approved",
    maskPendingValue: "Pending review",
    maskPointsLabel: "Polygon points",
    createMaskFromRegionAction: "Create mask from region",
    refreshMaskFromRegionAction: "Create new mask version",
    creatingMaskAction: "Creating mask...",
    approveMaskAction: "Approve cleanup mask",
    approvingMaskAction: "Approving mask...",
    regionTypeLabels: {
      speech_balloon: "Speech balloon",
      narration_box: "Narration box",
      free_text: "Free text",
      sfx: "SFX",
      unknown: "Unknown",
    },
    regionStateLabels: {
      draft: "Draft",
      reviewed: "Reviewed",
      approved: "Approved",
      rejected: "Rejected",
    },
    regionOriginLabels: {
      detected: "Detected",
      user_created: "User created",
      user_split: "User split",
      user_merged: "User merged",
    },
    adjustBoundsLabel: "Bounding box controls",
    moveLeftAction: "Move left",
    moveUpAction: "Move up",
    moveDownAction: "Move down",
    moveRightAction: "Move right",
    narrowerAction: "Narrower",
    widerAction: "Wider",
    shorterAction: "Shorter",
    tallerAction: "Taller",
    jobsTitle: "Automation queue",
    jobsCopy:
      "This automation rail now covers region detection, cleanup previews, OCR extraction, automatic translation, and first-pass dialogue matching with visible page-level history.",
    jobsLoading: "Loading page jobs...",
    jobsEmpty: "No jobs have been queued for this page yet.",
    jobLoadErrorFallback: "The editor could not load the page job history.",
    jobCreateErrorFallback: "The editor could not queue the selected automation right now.",
    queuedJobsNotice:
      "There are queued jobs on this page. You can still reset or delete regions; queued region jobs will be cleared automatically.",
    runningJobsNotice:
      "There is a running job on this page. Wait for it to finish before editing or removing regions.",
    textLoadErrorFallback: "The editor could not load the saved dialogue workflow for this page.",
    textSaveErrorFallback: "The editor could not save the selected dialogue workflow right now.",
    approvedMasksSummary: "{count} approved active cleanup masks ready",
    ocrCandidatesSummary: "{count} OCR-ready regions available",
    unassignedDialoguesSummary: "{count} dialogues still need automatic matching",
    queueDetectionAction: "Queue region detection",
    queuingDetectionAction: "Queuing detection...",
    queueCleanupAction: "Queue cleanup preview",
    queuingCleanupAction: "Queuing cleanup...",
    queueOcrAction: "Queue OCR extraction",
    queuingOcrAction: "Queuing OCR...",
    queueTranslationAction: "Queue automatic translation",
    queuingTranslationAction: "Queuing translation...",
    queueMatchingAction: "Queue dialogue matching",
    queuingMatchingAction: "Queuing matching...",
    jobTypeLabels: {
      detect_regions: "Region detection",
      generate_cleanup: "Cleanup generation",
      run_ocr: "OCR",
      generate_translation: "Translation",
      match_dialogue: "Dialogue matching",
      generate_typesetting: "Typesetting",
      export_project: "Export",
    },
    jobStatusLabels: {
      queued: "Queued",
      running: "Running",
      succeeded: "Succeeded",
      failed: "Failed",
      canceled: "Canceled",
    },
    kicker: "Page editor shell",
    canvasCopy:
      "The original uploaded page now carries real persisted review regions. This gives us a dependable base for cleanup masks, dialogue mapping, and later automation.",
    showRegionsAction: "Show overlays",
    hideRegionsAction: "Hide overlays",
    addRegionAction: "Add review region",
    creatingRegionAction: "Adding region...",
    markReviewedAction: "Mark reviewed",
    approveRegionAction: "Approve region",
    resetRegionAction: "Reset to draft",
    deleteRegionAction: "Delete region",
    deletingRegionAction: "Deleting region...",
    resetRegionsAction: "Reset regions",
    resettingRegionsAction: "Resetting regions...",
    textSectionTitle: "Dialogue workflow",
    textSectionCopy:
      "Manual edits now live beside OCR, automatic translation, and first-pass matching so the human review loop stays in one place.",
    textLoading: "Loading page dialogue workflow...",
    dialoguesEmpty: "No dialogue has been saved for this page yet. Start a new one from the form below.",
    dialogueOrderLabel: "Line {order}",
    dialogueAssignedValue: "Assigned",
    dialogueUnassignedValue: "Unassigned",
    translationEmptyValue: "No translated text yet.",
    selectDialogueAction: "Select dialogue",
    selectedDialogueAction: "Selected dialogue",
    dialogueEditingLabel: "Editing target",
    editingDialogueValue: "Line {order}",
    newDialogueValue: "New dialogue",
    sourceTextLabel: "Source text",
    translationTextLabel: "Translated text",
    dialogueRegionHint: "This save will assign the dialogue to the selected {region}.",
    dialogueRegionMissingHint:
      "Select a region first if you want this dialogue to create an assignment and text placement automatically.",
    sourceTextRequired: "Source text is required before saving a dialogue.",
    createDialogueAction: "Create dialogue workflow",
    updateDialogueAction: "Update dialogue workflow",
    savingDialogueAction: "Saving dialogue workflow...",
    newDialogueAction: "Start new dialogue",
    adjustTextBoxLabel: "Text box controls",
    exportJpegAction: "Export JPG",
    exportingJpegAction: "Exporting JPG...",
    exportJpegErrorFallback: "The editor could not export the current page as JPG right now.",
    exportPdfAction: "Export PDF",
    exportingPdfAction: "Exporting PDF...",
    exportPdfErrorFallback: "The editor could not export the current page as PDF right now.",
    exportPsdAction: "Export PSD",
    exportingPsdAction: "Exporting PSD...",
    exportPsdErrorFallback: "The editor could not export the current page as PSD right now.",
    overlayRegionCount: "{count} saved regions",
    canvasEmptyState: "No review regions yet. Create one to anchor the editor workflow.",
    dimensionsFallbackNotice:
      "This page does not have stored dimensions yet, so the editor is using a fallback canvas proportion until a real image size is available.",
    cleanupPreviewTitle: "Cleanup compare",
    cleanupPreviewCopy:
      "Once cleanup runs, the editor keeps the original page for review and shows the generated cleaned preview beside it.",
    cleanupPreviewEmpty:
      "No cleaned preview exists yet. Approve at least one active mask and queue cleanup to generate the first comparison.",
    originalPreviewLabel: "Original",
    cleanedPreviewLabel: "Cleanup preview",
  },
};
