// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { GraphEdge } from "@/lib/types";

export function EdgeList({
  edges,
  selectedId,
  onSelect,
}: {
  edges: GraphEdge[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}) {
  return (
    <section aria-labelledby="links-heading">
      <h2 id="links-heading" className="text-[15px] font-semibold">
        Links ({edges.length})
      </h2>
      <ul className="mt-2 border border-line rounded-[2px] bg-surface divide-y divide-line">
        {edges.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              aria-pressed={e.id === selectedId}
              onClick={() => onSelect(e.id)}
              className="w-full px-3 py-2 text-left font-mono text-[13px] aria-pressed:bg-accent/15 aria-pressed:text-accent"
            >
              {e.source} {e.type} {e.target}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
