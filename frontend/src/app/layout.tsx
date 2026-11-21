// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Evidence-first impact workbench (working title)",
  description:
    "Fictional, synthetic-data workbench for tracing configuration links back to their sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
