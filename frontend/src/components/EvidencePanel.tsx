// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { GraphEdge } from "@/lib/types";

const ORDER = ["file", "sheet", "cell", "page"];

// The breadcrumb follows the locator hierarchy (file, sheet, cell); unknown keys follow in key order.
function crumbs(locator: Record<string, string>): string[] {
  const keys = Object.keys(locator).sort(
    (a, b) => (ORDER.indexOf(a) + 99) % 99 - (ORDER.indexOf(b) + 99) % 99 || a.localeCompare(b),
  );
  return keys.map((k) => locator[k]);
}

export function EvidencePanel({ edge }: { edge: GraphEdge | undefined }) {
  return (
    <section
      role="region"
      aria-label="Evidence"
      className="border border-line rounded-[2px] bg-surface p-4 md:sticky md:top-4"
    >
      {edge ? (
        <>
          <h2 className="text-[15px] font-semibold">Evidence for this link</h2>
          <p className="mt-3 break-words font-mono text-[13px]">{crumbs(edge.locator.locator).join(" › ")}</p>
          <blockquote className="mt-2 border-l-2 border-accent pl-3 break-words">{edge.locator.snippet}</blockquote>
          <p className="mt-3 inline-block border border-line rounded-[2px] px-2 py-0.5 text-[13px] text-muted">
            Fake locator: no real file behind it
          </p>
        </>
      ) : (
        <p className="max-w-[70ch] text-muted">
          Select a link in the graph or the list to see where it comes from.
        </p>
      )}
    </section>
  );
}
