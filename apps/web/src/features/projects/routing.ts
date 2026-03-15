import type { SupportedUiLocale } from "../../i18n/config.ts";

export function buildProjectWorkspaceHref(locale: SupportedUiLocale, projectId: string) {
  return `/${locale}/projects/${projectId}` as const;
}

export function buildProjectPageEditorHref(
  locale: SupportedUiLocale,
  projectId: string,
  pageId: string,
) {
  return `/${locale}/projects/${projectId}/pages/${pageId}` as const;
}
