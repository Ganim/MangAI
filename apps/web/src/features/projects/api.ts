import {
  parseAssignmentResponse,
  parseCreateMaskRevisionRequest,
  parseCreatePageRegionRequest,
  parseCreatePageJobRequest,
  parseCreateProjectRequest,
  parseCreateProjectResponse,
  parseDialogueResponse,
  parseListPageAssignmentsResponse,
  parseListPageDialoguesResponse,
  parseListPageJobsResponse,
  parseListPageMaskRevisionsResponse,
  parseListPagePlacementsResponse,
  parseListProjectsResponse,
  parseListPageRegionsResponse,
  parseListPageTranslationsResponse,
  parseMaskRevisionResponse,
  parsePlacementResponse,
  parsePageJobResponse,
  parsePageRegionResponse,
  parseProjectDetailResponse,
  parseRegisterProjectPagesResponse,
  parseTranslationResponse,
  parseUpdateMaskRevisionRequest,
  parseUpdatePageRegionRequest,
  parseManualDialogueRequest,
  parseUpsertAssignmentRequest,
  parseUpsertPlacementRequest,
  parseUpsertTranslationRequest,
} from "@mangai/shared";

import { getPublicApiBaseUrl } from "../../config/env.ts";

export class ApiClientError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
  }
}

type CreateProjectInput = {
  name: string;
  source_language: string;
  target_language: string;
  target_text_direction?: "ltr" | "rtl" | "ttb";
};

type RegisterPagesInput = {
  files: File[];
};

type CreatePageRegionInput = {
  type: "speech_balloon" | "narration_box" | "free_text" | "sfx" | "unknown";
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
};

type UpdatePageRegionInput = {
  type?: "speech_balloon" | "narration_box" | "free_text" | "sfx" | "unknown";
  state?: "draft" | "reviewed" | "approved" | "rejected";
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  text_area?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  context_area?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  global_reading_order?: number;
};

type PolygonPointInput = {
  x: number;
  y: number;
};

type PolygonShapeInput = {
  type: "polygon";
  points: PolygonPointInput[];
};

type CreateMaskRevisionInput = {
  region_id: string;
  shape: PolygonShapeInput;
};

type UpdateMaskRevisionInput = {
  approved?: boolean;
  is_active?: boolean;
  shape?: PolygonShapeInput;
};

type CreatePageJobInput = {
  type:
    | "detect_regions"
    | "generate_cleanup"
    | "run_ocr"
    | "generate_translation"
    | "match_dialogue"
    | "generate_typesetting"
    | "export_project";
};

type ManualDialogueInput = {
  page_id: string;
  content: string;
  source_language: string;
  reading_order: number;
};

type UpsertTranslationInput = {
  dialogue_id: string;
  target_language: string;
  text_direction?: "ltr" | "rtl" | "ttb";
  content: string;
  status: "draft" | "reviewed" | "approved";
};

type UpsertAssignmentInput = {
  dialogue_id: string;
  region_id: string;
  origin: "automatic" | "manual";
  approved: boolean;
};

type UpsertPlacementInput = {
  assignment_id: string;
  text_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  style: {
    font_family: string;
    font_fallbacks?: string[];
    font_size: number;
    leading: number;
    tracking: number;
    alignment: string;
    direction: "ltr" | "rtl" | "ttb";
    rotation: number;
    fill: string;
  };
};

async function readJsonResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

async function requestJson<T>(
  path: string,
  init: RequestInit,
  parser: (value: unknown) => T,
): Promise<T> {
  const response = await fetch(`${getPublicApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  const payload = await readJsonResponse(response);

  if (!response.ok) {
    const errorPayload =
      payload && typeof payload === "object"
        ? (payload as { error_code?: string; message?: string })
        : undefined;
    throw new ApiClientError(
      errorPayload?.error_code ?? "API_REQUEST_FAILED",
      errorPayload?.message ?? `Request failed with status ${response.status}.`,
    );
  }

  return parser(payload);
}

export async function listProjects() {
  return requestJson("/projects", { method: "GET" }, parseListProjectsResponse);
}

export function resolveApiAssetUrl(assetPath: string) {
  return new URL(assetPath, `${getPublicApiBaseUrl()}/`).toString();
}

export async function getProjectDetail(projectId: string) {
  return requestJson(`/projects/${projectId}`, { method: "GET" }, parseProjectDetailResponse);
}

export async function getPageRegions(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/regions`,
    { method: "GET" },
    parseListPageRegionsResponse,
  );
}

export async function getPageJobs(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/jobs`,
    { method: "GET" },
    parseListPageJobsResponse,
  );
}

export async function getPageMaskRevisions(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/mask-revisions`,
    { method: "GET" },
    parseListPageMaskRevisionsResponse,
  );
}

export async function getPageDialogues(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/dialogues`,
    { method: "GET" },
    parseListPageDialoguesResponse,
  );
}

export async function getPageTranslations(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/translations`,
    { method: "GET" },
    parseListPageTranslationsResponse,
  );
}

export async function getPageAssignments(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/assignments`,
    { method: "GET" },
    parseListPageAssignmentsResponse,
  );
}

export async function getPagePlacements(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/placements`,
    { method: "GET" },
    parseListPagePlacementsResponse,
  );
}

export async function createProject(input: CreateProjectInput) {
  const payload = parseCreateProjectRequest(input);
  return requestJson(
    "/projects",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    parseCreateProjectResponse,
  );
}

export async function registerProjectPages(projectId: string, input: RegisterPagesInput) {
  const formData = new FormData();
  for (const file of input.files) {
    formData.append("files", file, file.name);
  }

  const response = await fetch(`${getPublicApiBaseUrl()}/projects/${projectId}/pages/upload`, {
    method: "POST",
    body: formData,
  });

  const payload = await readJsonResponse(response);
  if (!response.ok) {
    const errorPayload =
      payload && typeof payload === "object"
        ? (payload as { error_code?: string; message?: string })
        : undefined;
    throw new ApiClientError(
      errorPayload?.error_code ?? "API_REQUEST_FAILED",
      errorPayload?.message ?? `Request failed with status ${response.status}.`,
    );
  }

  return parseRegisterProjectPagesResponse(payload);
}

export async function createPageRegion(
  projectId: string,
  pageId: string,
  input: CreatePageRegionInput,
) {
  const payload = parseCreatePageRegionRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/regions`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    parsePageRegionResponse,
  );
}

export async function updatePageRegion(
  projectId: string,
  pageId: string,
  regionId: string,
  input: UpdatePageRegionInput,
) {
  const payload = parseUpdatePageRegionRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/regions/${regionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    parsePageRegionResponse,
  );
}

export async function deletePageRegion(projectId: string, pageId: string, regionId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/regions/${regionId}`,
    {
      method: "DELETE",
    },
    parseListPageRegionsResponse,
  );
}

export async function resetPageRegions(projectId: string, pageId: string) {
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/regions/reset`,
    {
      method: "POST",
    },
    parseListPageRegionsResponse,
  );
}

export async function createMaskRevision(
  projectId: string,
  pageId: string,
  input: CreateMaskRevisionInput,
) {
  const payload = parseCreateMaskRevisionRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/mask-revisions`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    parseMaskRevisionResponse,
  );
}

export async function updateMaskRevision(
  projectId: string,
  pageId: string,
  maskRevisionId: string,
  input: UpdateMaskRevisionInput,
) {
  const payload = parseUpdateMaskRevisionRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/mask-revisions/${maskRevisionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    parseMaskRevisionResponse,
  );
}

export async function createManualDialogue(
  projectId: string,
  pageId: string,
  input: ManualDialogueInput,
) {
  const payload = parseManualDialogueRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/dialogues`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    parseDialogueResponse,
  );
}

export async function updateManualDialogue(
  projectId: string,
  pageId: string,
  dialogueId: string,
  input: ManualDialogueInput,
) {
  const payload = parseManualDialogueRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/dialogues/${dialogueId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    parseDialogueResponse,
  );
}

export async function upsertPageTranslation(
  projectId: string,
  pageId: string,
  input: UpsertTranslationInput,
) {
  const payload = parseUpsertTranslationRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/translations`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    parseTranslationResponse,
  );
}

export async function upsertPageAssignment(
  projectId: string,
  pageId: string,
  input: UpsertAssignmentInput,
) {
  const payload = parseUpsertAssignmentRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/assignments`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    parseAssignmentResponse,
  );
}

export async function upsertPagePlacement(
  projectId: string,
  pageId: string,
  input: UpsertPlacementInput,
) {
  const payload = parseUpsertPlacementRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/placements`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    parsePlacementResponse,
  );
}

export async function createPageJob(
  projectId: string,
  pageId: string,
  input: CreatePageJobInput,
) {
  const payload = parseCreatePageJobRequest(input);
  return requestJson(
    `/projects/${projectId}/pages/${pageId}/jobs`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    parsePageJobResponse,
  );
}
