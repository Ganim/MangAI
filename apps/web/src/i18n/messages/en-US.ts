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
    createAction: string;
    creatingAction: string;
    projectListTitle: string;
    projectListCopy: string;
    projectListEmpty: string;
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
    rejectionReasons: {
      unsupported_type: string;
      too_large: string;
      duplicate_name: string;
    };
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
      "This slice already talks to the API. You can create draft projects, inspect existing ones, and register a first upload batch as page metadata.",
    projectNameLabel: "Project name",
    projectNamePlaceholder: "Chapter 01 - Review pass",
    sourceLanguageLabel: "Source language",
    targetLanguageLabel: "Target language",
    createAction: "Create project",
    creatingAction: "Creating project...",
    projectListTitle: "Current project board",
    projectListCopy:
      "Each card reflects the API state. Select one project to become the active destination for the upload queue.",
    projectListEmpty: "No projects yet. Create the first one to unlock the upload queue.",
    pageCountLabel: "{count} registered pages",
    uploadTitle: "Prepare the first upload batch",
    uploadCopy:
      "Pick page files from your machine, review the queue, and register them into the selected project. Binary storage will come in the next slice; for now we are locking the metadata flow.",
    selectedProjectLabel: "Active project",
    noProjectSelected: "Select or create a project first",
    chooseFilesAction: "Choose page files",
    uploadQueueEmpty: "No pages in the queue yet. Add JPEG, PNG, or WEBP files to continue.",
    dimensionsPending: "dimensions captured later",
    removeAction: "Remove",
    registerAction: "Register pages",
    registeringAction: "Registering pages...",
    uploadHint:
      "The current API accepts one metadata batch per action and already increments the project page count.",
    rejectionReasons: {
      unsupported_type: "{file}: unsupported file type. Use JPEG, PNG, or WEBP.",
      too_large: "{file}: file exceeds the current 25 MB limit.",
      duplicate_name: "{file}: duplicate file name detected in this queue.",
    },
  },
};
