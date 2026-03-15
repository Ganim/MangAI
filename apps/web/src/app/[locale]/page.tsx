import { notFound } from "next/navigation";

import { HomeShell } from "../../components/home-shell.tsx";
import { getMessages } from "../../i18n/index.ts";
import { resolveUiLocale } from "../../i18n/routing.ts";

type LocaleHomePageProps = {
  params: Promise<{ locale: string }>;
};

export default async function LocaleHomePage({ params }: LocaleHomePageProps) {
  const { locale: rawLocale } = await params;
  const locale = resolveUiLocale(rawLocale);

  if (locale === null) {
    notFound();
  }

  return <HomeShell locale={locale} messages={getMessages(locale)} />;
}
