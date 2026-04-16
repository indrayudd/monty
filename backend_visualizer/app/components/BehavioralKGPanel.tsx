"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import {
  api,
  type BehavioralNode,
  type BehavioralEdge,
} from "../lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
}) as unknown as React.ComponentType<Record<string, unknown>>;

const TYPE_COLORS: Record<string, string> = {
  setting_event: "#7c3aed", // violet
  antecedent: "#0ea5e9", // sky
  behavior: "#f97316", // orange
  function: "#10b981", // emerald
  brain_state: "#eab308", // amber-yellow (distinct from severity yellow via context)
  response: "#ec4899", // pink
  protective_factor: "#94a3b8", // muted slate
};

const REL_COLORS: Record<string, string> = {
  triggers: "#0ea5e9",
  serves: "#10b981",
  occurs_in: "#eab308",
  reinforces: "#22c55e",
  extinguishes: "#ef4444",
  "co-regulates": "#a855f7",
  recurs_with: "#f97316",
  predisposes: "#7c3aed",
  amplifies: "#f43f5e",
  gates: "#06b6d4",
  follows: "#94a3b8",
  evidences: "#10b981",
  undermines: "#ef4444",
};

export function BehavioralKGPanel({
  selectedSlug,
  onSelectNode,
}: {
  selectedSlug: string | null;
  onSelectNode: (slug: string | null) => void;
}) {
  const [nodes, setNodes] = useState<BehavioralNode[]>([]);
  const [edges, setEdges] = useState<BehavioralEdge[]>([]);
  const [minSupport, setMinSupport] = useState(2);
  const [degraded, setDegraded] = useState(false);
  const fgRef = useRef<unknown>(null);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.behavioralGraph(minSupport);
        if (!stop) {
          setNodes(r.nodes || []);
          setEdges(r.edges || []);
          setDegraded(false);
        }
      } catch {
        if (!stop) setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(i);
    };
  }, [minSupport]);

  const data = useMemo(
    () => ({
      nodes: nodes.map((n) => ({
        id: n.slug,
        name: n.title || n.slug,
        type: n.type,
        val: Math.max(2, Math.log2(1 + n.support_count) * 4),
        color: TYPE_COLORS[n.type] || "#6b7280",
        curiosity: n.curiosity_score,
      })),
      links: edges.map((e) => ({
        source: e.src_slug.split("/").pop()!,
        target: e.dst_slug.split("/").pop()!,
        width: Math.max(0.5, Math.log2(1 + e.support_count)),
        color: REL_COLORS[e.rel] || "#52525b",
        rel: e.rel,
      })),
    }),
    [nodes, edges],
  );

  const isEmpty = nodes.length === 0;

  return (
    <div className="relative h-full w-full bg-zinc-950 overflow-hidden">
      <div className="absolute top-2 left-2 z-10 bg-black/70 rounded p-2 text-[11px] text-white/80 font-mono border border-white/10">
        <div className="font-semibold mb-1 text-white">
          Behavioral KG <span className="text-white/40">(anonymized)</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
          {Object.entries(TYPE_COLORS).map(([t, c]) => (
            <div key={t} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: c }}
              />
              <span>{t.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute top-2 right-2 z-10 bg-black/70 rounded p-2 text-[11px] text-white/80 font-mono flex items-center gap-2 border border-white/10">
        <label>min support</label>
        <input
          type="number"
          min={1}
          value={minSupport}
          onChange={(e) =>
            setMinSupport(Math.max(1, parseInt(e.target.value || "1")))
          }
          className="bg-zinc-800 px-2 py-0.5 w-12 rounded text-white"
        />
        <span className="ml-2 text-white/40">
          {nodes.length}n · {edges.length}e
        </span>
      </div>
      {degraded && (
        <div className="absolute top-14 left-2 z-10 text-[10px] text-amber-300/80 font-mono bg-amber-950/40 border border-amber-500/20 rounded px-2 py-1">
          ⚠ behavioral-graph unreachable — last render retained
        </div>
      )}
      {isEmpty && !degraded && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-white/40 font-mono text-xs max-w-sm px-4">
            Awaiting first note — the agent has not seen any classroom
            observations yet.
          </div>
        </div>
      )}
      <ForceGraph2D
        ref={fgRef as unknown as React.Ref<unknown>}
        graphData={data}
        nodeRelSize={4}
        backgroundColor="rgba(9,9,11,0)"
        linkWidth={(l: unknown) => (l as { width: number }).width}
        linkColor={(l: unknown) => (l as { color: string }).color}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={0.85}
        nodeCanvasObject={(
          node: unknown,
          ctx: CanvasRenderingContext2D,
          globalScale: number,
        ) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const n = node as any;
          const r = n.val;
          // halo
          if (n.curiosity >= 0.7) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 6, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
            ctx.fill();
          } else if (n.curiosity >= 0.5) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(234, 179, 8, 0.25)";
            ctx.fill();
          }
          // selection ring
          if (n.id === selectedSlug) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
          // node body
          ctx.beginPath();
          ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = n.color;
          ctx.fill();
          if (globalScale > 1.6) {
            ctx.fillStyle = "white";
            ctx.font = `${(10 / globalScale) * 4}px sans-serif`;
            ctx.fillText(n.name, n.x + r + 2, n.y + 3);
          }
        }}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onNodeClick={(node: any) =>
          onSelectNode(node.id === selectedSlug ? null : node.id)
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onBackgroundClick={() => onSelectNode(null)}
      />
    </div>
  );
}
