"use client";

// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { useEffect, useState } from "react";

import { fetchImpact } from "@/lib/api";
import type { ImpactResponse } from "@/lib/types";
import { EdgeList } from "./EdgeList";
import { EvidencePanel } from "./EvidencePanel";
import { GraphView } from "./GraphView";
import { StatePanel } from "./StatePanel";

type Result = { entity: string; data?: ImpactResponse; error?: string };

export function Workspace({ entity }: { entity: string }) {
  const [result, setResult] = useState<Result>();
  const [selected, setSelected] = useState<{ entity: string; id: string }>();

  useEffect(() => {
    const ctl = new AbortController();
    fetchImpact(entity, ctl.signal)
      .then((data) => setResult({ entity, data }))
      .catch((e: unknown) => {
        if (!ctl.signal.aborted) setResult({ entity, error: e instanceof Error ? e.message : "Something went wrong. Reload the page." });
      });
    return () => ctl.abort();
  }, [entity]);

  // A result for another entity counts as loading, so a stale graph is never shown.
  const current = result?.entity === entity ? result : undefined;
  const data = current?.data;
  const selectedId = selected?.entity === entity ? selected.id : undefined;
  const edge = data?.edges.find((e) => e.id === selectedId);
  const select = (id: string) => setSelected({ entity, id });

  return (
    <>
      <p className="max-w-[70ch] text-muted">
        {data?.notice ?? "Tracer: shows stored links around one entity. This is not impact analysis."}
      </p>
      <div className="mt-4 grid gap-4 md:grid-cols-[3fr_2fr] md:items-start">
        <div className="flex flex-col gap-4">
          {!current && <StatePanel kind="loading" entity={entity} />}
          {current?.error && <StatePanel kind="error" entity={entity} message={current.error} />}
          {data && data.edges.length === 0 && <StatePanel kind="empty" entity={entity} />}
          {data && data.edges.length > 0 && (
            <>
              <GraphView data={data} selectedId={selectedId} onSelect={select} />
              <EdgeList edges={data.edges} selectedId={selectedId} onSelect={select} />
            </>
          )}
        </div>
        <EvidencePanel edge={edge} />
      </div>
    </>
  );
}
