// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { FictionalBanner } from "@/components/FictionalBanner";

export default function Home() {
  return (
    <>
      <FictionalBanner />
      <main className="p-6">
        <h1 className="text-2xl font-semibold">
          Evidence-first impact workbench (working title)
        </h1>
      </main>
    </>
  );
}
