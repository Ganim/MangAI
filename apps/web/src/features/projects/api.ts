import {
  parseCreateProjectRequest,
  parseCreateProjectResponse,
  parseListProjectsResponse,
  parseProjectDetailResponse,
  parseRegisterProjectPagesResponse,
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
  return `${getPublicApiBaseUrl()}${assetPath}`;
}

export async function getProjectDetail(projectId: string) {
  return requestJson(`/projects/${projectId}`, { method: "GET" }, parseProjectDetailResponse);
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
