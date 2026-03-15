import { notFound } from "next/navigation";

import { ProjectWorkspace } from "../../../../components/project-workspace.tsx";
import { getMessages } from "../../../../i18n/index.ts";
import { resolveUiLocale } from "../../../../i18n/routing.ts";

type ProjectWorkspacePageProps = {
  params: Promise<{ locale: string; projectId: string }>;
};

export default async function ProjectWorkspacePage({ params }: ProjectWorkspacePageProps) {
  const { locale: rawLocale, projectId } = await params;
  const locale = resolveUiLocale(rawLocale);

  if (locale === null) {
    notFound();
  }

  return <ProjectWorkspace locale={locale} messages={getMessages(locale)} projectId={projectId} />;
}
