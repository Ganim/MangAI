import type { ReactNode } from "react";
import { notFound } from "next/navigation";

import { SUPPORTED_UI_LOCALES } from "@mangai/shared";

import { resolveUiLocale } from "../../i18n/routing.ts";

type LocaleLayoutProps = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export const dynamicParams = false;

export function generateStaticParams() {
  return SUPPORTED_UI_LOCALES.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: LocaleLayoutProps) {
  const { locale } = await params;
  const resolvedLocale = resolveUiLocale(locale);
  if (resolvedLocale === null) {
    notFound();
  }
  return (
    <div data-ui-locale={resolvedLocale} lang={resolvedLocale}>
      {children}
    </div>
  );
}
