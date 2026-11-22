"use client";

// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import "@xyflow/react/dist/style.css";

import { Handle, MarkerType, Position, ReactFlow, type Edge, type NodeProps, type NodeTypes } from "@xyflow/react";
import { useMemo, useSyncExternalStore } from "react";

import { toFlow, VSTEP, type NodeData, type Orientation } from "@/lib/graph";
import type { NeighbourhoodResponse } from "@/lib/types";

function EntityNode({ data }: NodeProps & { data: NodeData }) {
  return (
    <div
      className={`w-[120px] rounded-[2px] bg-surface px-3 py-2 ${data.seed ? "border-2 border-accent" : "border border-line"}`}
    >
      <Handle id="in-t" type="target" position={Position.Top} isConnectable={false} className="!opacity-0" />
      <Handle id="out-t" type="source" position={Position.Top} isConnectable={false} className="!opacity-0" />
      <Handle id="in-l" type="target" position={Position.Left} isConnectable={false} className="!opacity-0" />
      <Handle id="out-l" type="source" position={Position.Left} isConnectable={false} className="!opacity-0" />
      <div className="font-mono text-[13px] text-ink">{data.entityKey}</div>
      <div className="text-[13px] text-muted">{data.entityType}</div>
      <Handle id="in-r" type="target" position={Position.Right} isConnectable={false} className="!opacity-0" />
      <Handle id="out-r" type="source" position={Position.Right} isConnectable={false} className="!opacity-0" />
      <Handle id="in-b" type="target" position={Position.Bottom} isConnectable={false} className="!opacity-0" />
      <Handle id="out-b" type="source" position={Position.Bottom} isConnectable={false} className="!opacity-0" />
    </div>
  );
}

const NARROW = "(max-width: 767px)";

// Narrow screens stack the nodes so the text stays at its real size; no matchMedia (jsdom, SSR) means horizontal.
function subscribe(cb: () => void) {
  if (typeof window.matchMedia !== "function") return () => {};
  const mq = window.matchMedia(NARROW);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}
const narrow = () => typeof window.matchMedia === "function" && window.matchMedia(NARROW).matches;

const nodeTypes: NodeTypes = { entity: EntityNode as NodeTypes[string] };

export function GraphView({
  data,
  selectedId,
  onSelect,
}: {
  data: NeighbourhoodResponse;
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}) {
  const isNarrow = useSyncExternalStore(subscribe, narrow, () => false);
  const orientation: Orientation = isNarrow ? "vertical" : "horizontal";
  const flow = useMemo(() => toFlow(data, orientation), [data, orientation]);
  const edges: Edge[] = flow.edges.map((e) => ({
    ...e,
    selected: e.id === selectedId,
    interactionWidth: 24,
    markerEnd: { type: MarkerType.ArrowClosed, color: e.id === selectedId ? "var(--accent)" : "var(--muted)" },
    style: { stroke: e.id === selectedId ? "var(--accent)" : "var(--muted)", strokeWidth: e.id === selectedId ? 2 : 1 },
  }));
  return (
    <div
      className="border border-line rounded-[2px] bg-surface md:h-[360px]"
      style={isNarrow ? { height: flow.nodes.length * VSTEP + 40 } : undefined}
      role="group"
      aria-label="Graph of stored links; the link list below is the keyboard equivalent"
    >
      <ReactFlow
        key={orientation}
        nodes={flow.nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: "24px" }}
        nodesDraggable={false}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
        onEdgeClick={(_, edge) => onSelect(edge.id)}
      />
    </div>
  );
}
