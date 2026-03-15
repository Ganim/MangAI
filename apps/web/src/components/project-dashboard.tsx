"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import type { AppMessages } from "../i18n/index.ts";
import type { SupportedUiLocale } from "../i18n/config.ts";
import {
  ApiClientError,
  createProject,
  getProjectDetail,
  listProjects,
  registerProjectPages,
  resolveApiAssetUrl,
} from "../features/projects/api.ts";
import { buildProjectWorkspaceHref } from "../features/projects/routing.ts";
import {
  createUploadQueue,
  formatBytes,
  removeUploadQueueItem,
  SUPPORTED_UPLOAD_MIME_TYPES,
  type UploadQueueItem,
  type UploadQueueRejection,
} from "../features/projects/upload.ts";

type ProjectSummary = Awaited<ReturnType<typeof listProjects>>["projects"][number];
type ProjectPage = Awaited<ReturnType<typeof getProjectDetail>>["pages"][number];

type ProjectDashboardProps = {
  locale: SupportedUiLocale;
  messages: AppMessages;
};

type ProjectFormState = {
  name: string;
  source_language: string;
  target_language: string;
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

export function ProjectDashboard({ locale, messages }: ProjectDashboardProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [apiState, setApiState] = useState<"loading" | "online" | "offline">("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [pageLoadError, setPageLoadError] = useState<string | null>(null);
  const [projectPages, setProjectPages] = useState<ProjectPage[]>([]);
  const [isLoadingPages, setIsLoadingPages] = useState(false);
  const [queue, setQueue] = useState<UploadQueueItem<File>[]>([]);
  const [rejections, setRejections] = useState<UploadQueueRejection[]>([]);
  const [isCreating, startCreateTransition] = useTransition();
  const [isUploading, startUploadTransition] = useTransition();
  const [formState, setFormState] = useState<ProjectFormState>({
    name: "",
    source_language: messages.dashboard.sourceLanguageOptions[0]?.value ?? "ja-JP",
    target_language: locale,
  });

  useEffect(() => {
    let canceled = false;

    async function loadProjects() {
      setApiState("loading");
      setLoadError(null);
      try {
        const response = await listProjects();
        if (canceled) {
          return;
        }

        setProjects(response.projects);
        setApiState("online");
        setSelectedProjectId((currentValue) => currentValue ?? response.projects[0]?.id ?? null);
      } catch (error) {
        if (canceled) {
          return;
        }

        setApiState("offline");
        setLoadError(getErrorMessage(error, messages.dashboard.loadErrorFallback));
      }
    }

    void loadProjects();

    return () => {
      canceled = true;
    };
  }, [messages.dashboard.loadErrorFallback]);

  const selectedProject =
    projects.find((project) => project.id === selectedProjectId) ?? projects[0] ?? null;

  useEffect(() => {
    if (selectedProjectId === null) {
      setProjectPages([]);
      setPageLoadError(null);
      setIsLoadingPages(false);
      return;
    }

    const projectId: string = selectedProjectId;
    let canceled = false;

    async function loadProjectDetail() {
      setIsLoadingPages(true);
      setPageLoadError(null);

      try {
        const response = await getProjectDetail(projectId);
        if (canceled) {
          return;
        }
        setProjectPages(response.pages);
        setApiState("online");
      } catch (error) {
        if (canceled) {
          return;
        }
        setPageLoadError(getErrorMessage(error, messages.dashboard.loadErrorFallback));
      } finally {
        if (!canceled) {
          setIsLoadingPages(false);
        }
      }
    }

    void loadProjectDetail();

    return () => {
      canceled = true;
    };
  }, [messages.dashboard.loadErrorFallback, selectedProjectId]);

  function handleProjectSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    setUploadSuccess(null);

    startCreateTransition(async () => {
      try {
        const response = await createProject(formState);
        setProjects((currentValue) => [response.project, ...currentValue]);
        setSelectedProjectId(response.project.id);
        setFormState({
          name: "",
          source_language: messages.dashboard.sourceLanguageOptions[0]?.value ?? "ja-JP",
          target_language: locale,
        });
        setApiState("online");
      } catch (error) {
        setCreateError(getErrorMessage(error, messages.dashboard.createErrorFallback));
      }
    });
  }

  function handleFileSelection(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    const preparedQueue = createUploadQueue(files);

    setQueue(preparedQueue.accepted);
    setRejections(preparedQueue.rejected);
    setUploadError(null);
    setUploadSuccess(null);
    event.target.value = "";
  }

  function handleRegisterPages() {
    if (selectedProject === null || queue.length === 0) {
      return;
    }

    setUploadError(null);
    setUploadSuccess(null);

    startUploadTransition(async () => {
      try {
        const response = await registerProjectPages(
          selectedProject.id,
          { files: queue.map((item) => item.file) },
        );
        setProjects((currentValue) =>
          currentValue.map((project) =>
            project.id === response.project.id ? response.project : project,
          ),
        );
        setProjectPages((currentValue) =>
          [...currentValue, ...response.pages].sort((left, right) => left.index - right.index),
        );
        setSelectedProjectId(response.project.id);
        setQueue([]);
        setRejections([]);
        setUploadSuccess(
          messages.dashboard.uploadSuccess.replace("{count}", String(response.pages.length)),
        );
        setApiState("online");
      } catch (error) {
        setUploadError(getErrorMessage(error, messages.dashboard.uploadErrorFallback));
      }
    });
  }

  return (
    <section className="dashboard-grid" id="workspace">
      <article className="section-panel">
        <div className="section-head">
          <div className="section-kicker-row">
            <span className="eyebrow">{messages.dashboard.kicker}</span>
            <span className={`api-badge api-badge-${apiState}`}>
              {apiState === "online"
                ? messages.dashboard.apiOnline
                : apiState === "offline"
                  ? messages.dashboard.apiOffline
                  : messages.dashboard.apiLoading}
            </span>
          </div>
          <h2 className="section-title">{messages.dashboard.projectTitle}</h2>
          <p className="section-copy">{messages.dashboard.projectCopy}</p>
        </div>

        {loadError ? <p className="notice notice-error">{loadError}</p> : null}
        {createError ? <p className="notice notice-error">{createError}</p> : null}

        <form className="project-form" onSubmit={handleProjectSubmit}>
          <label className="field">
            <span className="field-label">{messages.dashboard.projectNameLabel}</span>
            <input
              className="field-input"
              name="name"
              value={formState.name}
              onChange={(event) =>
                setFormState((currentValue) => ({
                  ...currentValue,
                  name: event.target.value,
                }))
              }
              placeholder={messages.dashboard.projectNamePlaceholder}
              required
            />
          </label>

          <div className="field-row">
            <label className="field">
              <span className="field-label">{messages.dashboard.sourceLanguageLabel}</span>
              <select
                className="field-input"
                name="source_language"
                value={formState.source_language}
                onChange={(event) =>
                  setFormState((currentValue) => ({
                    ...currentValue,
                    source_language: event.target.value,
                  }))
                }
                required
              >
                {messages.dashboard.sourceLanguageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label} ({option.value})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field-label">{messages.dashboard.targetLanguageLabel}</span>
              <select
                className="field-input"
                name="target_language"
                value={formState.target_language}
                onChange={(event) =>
                  setFormState((currentValue) => ({
                    ...currentValue,
                    target_language: event.target.value,
                  }))
                }
                required
              >
                {messages.dashboard.targetLanguageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label} ({option.value})
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button className="primary-button" disabled={isCreating} type="submit">
            {isCreating ? messages.dashboard.creatingAction : messages.dashboard.createAction}
          </button>
        </form>
      </article>

      <article className="section-panel">
        <div className="section-head">
          <h2 className="section-title">{messages.dashboard.projectListTitle}</h2>
          <p className="section-copy">{messages.dashboard.projectListCopy}</p>
        </div>

        {projects.length === 0 ? (
          <p className="empty-state">{messages.dashboard.projectListEmpty}</p>
        ) : (
          <div className="project-list">
            {projects.map((project) => {
              const isSelected = project.id === selectedProject?.id;
              return (
                <button
                  key={project.id}
                  className={isSelected ? "project-card project-card-selected" : "project-card"}
                  onClick={() => setSelectedProjectId(project.id)}
                  type="button"
                >
                  <span className="project-card-title">{project.name}</span>
                  <span className="project-card-meta">
                    {project.source_language}
                    {" -> "}
                    {project.target_language}
                  </span>
                  <span className="project-card-meta">
                    {messages.dashboard.pageCountLabel.replace(
                      "{count}",
                      String(project.page_count),
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <div className="workspace-inline-actions">
          <Link
            className={
              selectedProject ? "primary-button" : "primary-button primary-button-disabled"
            }
            href={selectedProject ? buildProjectWorkspaceHref(locale, selectedProject.id) : "#"}
            onClick={(event) => {
              if (!selectedProject) {
                event.preventDefault();
              }
            }}
          >
            {messages.dashboard.openProjectAction}
          </Link>
        </div>
      </article>

      <article className="section-panel dashboard-span-2">
        <div className="section-head">
          <h2 className="section-title">{messages.dashboard.uploadTitle}</h2>
          <p className="section-copy">{messages.dashboard.uploadCopy}</p>
        </div>

        <div className="upload-toolbar">
          <div className="upload-summary">
            <span className="upload-summary-label">{messages.dashboard.selectedProjectLabel}</span>
            <strong>{selectedProject?.name ?? messages.dashboard.noProjectSelected}</strong>
          </div>

          <label className="secondary-button upload-input-button">
            <input
              accept={SUPPORTED_UPLOAD_MIME_TYPES.join(",")}
              className="visually-hidden"
              multiple
              onChange={handleFileSelection}
              type="file"
            />
            {messages.dashboard.chooseFilesAction}
          </label>
        </div>

        {uploadError ? <p className="notice notice-error">{uploadError}</p> : null}
        {uploadSuccess ? <p className="notice notice-success">{uploadSuccess}</p> : null}
        {pageLoadError ? <p className="notice notice-error">{pageLoadError}</p> : null}

        {rejections.length > 0 ? (
          <ul className="rejection-list">
            {rejections.map((rejection) => (
              <li key={`${rejection.file_name}-${rejection.reason}`} className="notice notice-warning">
                {messages.dashboard.rejectionReasons[rejection.reason].replace(
                  "{file}",
                  rejection.file_name,
                )}
              </li>
            ))}
          </ul>
        ) : null}

        {queue.length === 0 ? (
          <p className="empty-state">{messages.dashboard.uploadQueueEmpty}</p>
        ) : (
          <div className="upload-queue">
            {queue.map((item) => (
              <article className="upload-card" key={item.client_id}>
                <div>
                  <h3 className="card-title">{item.file_name}</h3>
                  <p className="card-description">
                    {item.mime_type} · {formatBytes(item.size_bytes)} ·{" "}
                    {messages.dashboard.dimensionsPending}
                  </p>
                </div>

                <button
                  className="ghost-button"
                  onClick={() =>
                    setQueue((currentValue) => removeUploadQueueItem(currentValue, item.client_id))
                  }
                  type="button"
                >
                  {messages.dashboard.removeAction}
                </button>
              </article>
            ))}
          </div>
        )}

        <div className="upload-actions">
          <button
            className="primary-button"
            disabled={selectedProject === null || queue.length === 0 || isUploading}
            onClick={handleRegisterPages}
            type="button"
          >
            {isUploading ? messages.dashboard.registeringAction : messages.dashboard.registerAction}
          </button>
          <span className="upload-hint">{messages.dashboard.uploadHint}</span>
        </div>

        <div className="section-head section-head-compact">
          <h3 className="section-title">{messages.dashboard.pagesTitle}</h3>
          <p className="section-copy">{messages.dashboard.pagesCopy}</p>
        </div>

        {isLoadingPages ? (
          <p className="empty-state">{messages.dashboard.pagesLoading}</p>
        ) : projectPages.length === 0 ? (
          <p className="empty-state">{messages.dashboard.pagesEmpty}</p>
        ) : (
          <div className="stored-pages-grid">
            {projectPages.map((page) => (
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
                    {messages.dashboard.pageIndexLabel.replace("{index}", String(page.index))}
                  </span>
                  <h3 className="card-title">{page.file_name}</h3>
                  <p className="card-description">
                    {page.mime_type} · {formatBytes(page.size_bytes)}
                  </p>
                  <p className="card-description">{messages.dashboard.storedOriginalLabel}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
