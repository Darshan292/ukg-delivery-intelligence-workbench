// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { FictionalBanner } from "@/components/FictionalBanner";
import { Workspace } from "@/components/Workspace";

// Next 16: searchParams is a Promise.
export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ entity?: string | string[] }>;
}) {
  const { entity } = await searchParams;
  const key = (Array.isArray(entity) ? entity[0] : entity) || "RULE-T1";
  return (
    <>
      <FictionalBanner />
      <main className="mx-auto max-w-[1280px] p-4 md:p-6">
        <h1 className="mb-2 text-xl font-semibold tracking-[-0.01em]">
          Evidence-first impact workbench (working title)
        </h1>
        <Workspace entity={key} />
      </main>
    </>
  );
}
