import { notFound } from "next/navigation";

import { PageEditorShell } from "../../../../../../components/page-editor-shell.tsx";
import { getMessages } from "../../../../../../i18n/index.ts";
import { resolveUiLocale } from "../../../../../../i18n/routing.ts";

type PageEditorPageProps = {
  params: Promise<{ locale: string; projectId: string; pageId: string }>;
};

export default async function PageEditorPage({ params }: PageEditorPageProps) {
  const { locale: rawLocale, projectId, pageId } = await params;
  const locale = resolveUiLocale(rawLocale);

  if (locale === null) {
    notFound();
  }

  return (
    <PageEditorShell
      locale={locale}
      messages={getMessages(locale)}
      pageId={pageId}
      projectId={projectId}
    />
  );
}
