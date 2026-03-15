import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "MangAI",
  description:
    "AI-first manga localization workspace with human review, clean art generation, and Photoshop-friendly exports.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en-US">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
