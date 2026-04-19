"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { forceX, forceY } from "d3-force";
import {
  api,
  type BehavioralNode,
  type BehavioralEdge,
} from "../lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
}) as unknown as React.ComponentType<Record<string, unknown>>;

// From DESIGN.md § 2 "Behavioral Node Hues (The Functional Spectrum)"
const TYPE_COLORS: Record<string, string> = {
  setting_event: "#00D8FF",   // Cyan
  antecedent: "#BC8CFF",      // Purple
  behavior: "#FFA657",        // Orange
  function: "#FF7EB6",        // Magenta
  brain_state: "#79C0FF",     // Indigo
  response: "#3FB950",        // Teal
  protective_factor: "#94a3b8", // Muted slate (not in DESIGN.md, kept as neutral)
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
  const [minSupport, setMinSupport] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("monty_minSupport");
      return saved ? parseInt(saved) : 2;
    }
    return 2;
  });
  const [edgeFilter, setEdgeFilter] = useState<"all" | "observation" | "research">(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem("monty_edgeFilter") as "all" | "observation" | "research") || "all";
    }
    return "all";
  });
  const [degraded, setDegraded] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 800, h: 400 });
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<unknown>(null);

  const measureContainer = useCallback(() => {
    if (containerRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      if (clientWidth > 0 && clientHeight > 0) {
        setDims({ w: clientWidth, h: clientHeight });
      }
    }
  }, []);

  useEffect(() => {
    measureContainer();
    const ro = new ResizeObserver(measureContainer);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [measureContainer]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeObjRef = useRef<Map<string, any>>(new Map());
  const prevNodeSlugsRef = useRef<Set<string>>(new Set());
  const prevEdgeKeysRef = useRef<Set<string>>(new Set());
  const rawEdgesRef = useRef<BehavioralEdge[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });

  // Build links from current edges + filter + nodeMap
  const buildLinks = useCallback((edgesArr: BehavioralEdge[], nodeMap: Map<string, unknown>) => {
    return edgesArr
      .filter((e) => {
        if (edgeFilter === "research" && e.source !== "research") return false;
        if (edgeFilter === "observation" && e.source === "research") return false;
        const src = e.src_slug.split("/").pop()!;
        const dst = e.dst_slug.split("/").pop()!;
        return nodeMap.has(src) && nodeMap.has(dst);
      })
      .map((e) => ({
        source: e.src_slug.split("/").pop()!,
        target: e.dst_slug.split("/").pop()!,
        width: Math.max(0.8, Math.log2(1 + e.support_count)),
        color: e.source === "research" ? "rgba(255,255,255,0.6)" : (REL_COLORS[e.rel] || "#52525b"),
        rel: e.rel,
        edgeSource: e.source,
      }));
  }, [edgeFilter]);

  // Poll API — only update React state on structural changes
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.behavioralGraph(minSupport);
        if (stop) return;

        const newNodes = r.nodes || [];
        const newEdges = r.edges || [];
        rawEdgesRef.current = newEdges;
        const nodeMap = nodeObjRef.current;

        // Always mutate existing node properties in place (no re-render needed)
        const newSlugs = new Set<string>();
        let hasNewNodes = false;
        for (const n of newNodes) {
          newSlugs.add(n.slug);
          const existing = nodeMap.get(n.slug);
          if (existing) {
            existing.val = Math.max(2, Math.log2(1 + n.support_count) * 4);
            existing.curiosity = n.curiosity_score;
            existing.name = n.title || n.slug;
            existing.type = n.type;
            existing.color = TYPE_COLORS[n.type] || "#6b7280";
          } else {
            // New node — place near a random existing neighbor for organic entry
            const existingNodes = Array.from(nodeMap.values());
            const neighbor = existingNodes.length > 0
              ? existingNodes[Math.floor(Math.random() * existingNodes.length)]
              : null;
            nodeMap.set(n.slug, {
              id: n.slug,
              name: n.title || n.slug,
              type: n.type,
              val: Math.max(2, Math.log2(1 + n.support_count) * 4),
              color: TYPE_COLORS[n.type] || "#6b7280",
              curiosity: n.curiosity_score,
              // Start near a neighbor with offset for organic fade-in
              x: neighbor ? neighbor.x + (Math.random() - 0.5) * 60 : undefined,
              y: neighbor ? neighbor.y + (Math.random() - 0.5) * 60 : undefined,
              _enterTime: Date.now(),
            });
            hasNewNodes = true;
          }
        }
        // Remove departed nodes
        let hasRemovedNodes = false;
        for (const key of nodeMap.keys()) {
          if (!newSlugs.has(key)) { nodeMap.delete(key); hasRemovedNodes = true; }
        }

        // Check edge structural change
        const newEdgeKeys = new Set(newEdges.map((e) => `${e.src_slug}|${e.rel}|${e.dst_slug}`));
        const edgesChanged =
          newEdgeKeys.size !== prevEdgeKeysRef.current.size ||
          [...newEdgeKeys].some((k) => !prevEdgeKeysRef.current.has(k));

        // Only update React state (→ new graphData → simulation reheat) on structural changes
        if (hasNewNodes || hasRemovedNodes || edgesChanged ||
            prevNodeSlugsRef.current.size === 0) {
          prevNodeSlugsRef.current = newSlugs;
          prevEdgeKeysRef.current = newEdgeKeys;
          const links = buildLinks(newEdges, nodeMap);
          setGraphData({ nodes: Array.from(nodeMap.values()), links });
        }
        setDegraded(false);
      } catch {
        if (!stop) setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 4000);
    return () => { stop = true; clearInterval(i); };
  }, [minSupport, buildLinks]);

  // Rebuild links on edge filter change (no refetch needed)
  useEffect(() => {
    if (rawEdgesRef.current.length === 0) return;
    const links = buildLinks(rawEdgesRef.current, nodeObjRef.current);
    setGraphData((prev) => ({ nodes: prev.nodes, links }));
  }, [edgeFilter, buildLinks]);

  const data = graphData;
  const isEmpty = data.nodes.length === 0;

  return (
    <div ref={containerRef} className="relative h-full w-full bg-zinc-950 overflow-hidden">
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
      <div
        className="absolute top-2 right-2 z-10 bg-black/70 rounded p-2 text-[11px] text-white/80 font-mono flex items-center gap-2 border border-white/10"
        title="min support = minimum number of supporting observations for an edge to render. Increase to hide weak/noise edges; decrease (=1) to show everything, including single-observation links."
      >
        <label>min support</label>
        <input
          type="number"
          min={1}
          value={minSupport}
          onChange={(e) =>
            { const v = Math.max(1, parseInt(e.target.value || "1")); setMinSupport(v); localStorage.setItem("monty_minSupport", String(v)); }
          }
          className="bg-zinc-800 px-2 py-0.5 w-12 rounded text-white"
        />
        <span className="ml-2 text-white/40">
          {data.nodes.length}n · {data.links.length}e
        </span>
        <div className="ml-2 flex gap-0.5">
          {(["all", "observation", "research"] as const).map(f => (
            <button
              key={f}
              onClick={() => { setEdgeFilter(f); localStorage.setItem("monty_edgeFilter", f); }}
              className={`px-1.5 py-0.5 rounded text-[9px] transition-colors ${
                edgeFilter === f
                  ? f === "research" ? "bg-cyan-500/20 text-cyan-300" : "bg-white/15 text-white"
                  : "text-white/30 hover:text-white/60"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
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
        width={dims.w}
        height={dims.h}
        nodeRelSize={4}
        nodeLabel={() => ""}
        backgroundColor="rgba(9,9,11,0)"
        warmupTicks={40}
        cooldownTicks={200}
        cooldownTime={10000}
        d3AlphaDecay={0.0228}
        d3VelocityDecay={0.4}
        enableNodeDrag={true}
        onNodeDrag={(node: unknown) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const n = node as any;
          n.fx = n.x;
          n.fy = n.y;
        }}
        onNodeDragEnd={(node: unknown) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const n = node as any;
          n.fx = undefined;
          n.fy = undefined;
        }}
        onEngineTick={() => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fg = fgRef.current as any;
          if (!fg || fg._montyForcesTuned) return;
          if (fg.d3Force) {
            // D3 defaults with forceX/Y for disjoint subgraphs
            // (per Observable disjoint force-directed graph example)
            const charge = fg.d3Force("charge");
            if (charge) charge.strength(-30);
            fg.d3Force("x", forceX());
            fg.d3Force("y", forceY());
            fg._montyForcesTuned = true;
          }
        }}
        linkWidth={(l: unknown) => Math.max(0.8, (l as { width: number }).width)}
        linkColor={(l: unknown) => (l as { color: string }).color}
        linkLineDash={(l: unknown) => (l as { edgeSource?: string }).edgeSource === "research" ? [4, 2] : null}
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
          // Fade-in for new nodes: 0→1 over 800ms
          const age = n._enterTime ? Date.now() - n._enterTime : 1000;
          const opacity = Math.min(1, age / 100);
          if (opacity < 1) ctx.globalAlpha = opacity;
          // halo
          if (n.curiosity >= 0.7) {
            // ~1.5 Hz pulse, opacity 0.15..0.45
            const phase = (Date.now() % 700) / 700;
            const alpha = 0.15 + 0.30 * Math.abs(Math.sin(phase * Math.PI));
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 6 + 2 * Math.sin(phase * Math.PI), 0, 2 * Math.PI);
            ctx.fillStyle = `rgba(239, 68, 68, ${alpha.toFixed(3)})`;
            ctx.fill();
          } else if (n.curiosity >= 0.5) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(234, 179, 8, 0.25)";
            ctx.fill();
          }
          // hover ring — bright white outline so the hovered node is unmistakable
          if (n.id === hoveredId) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
            ctx.strokeStyle = "rgba(255,255,255,0.9)";
            ctx.lineWidth = 2;
            ctx.stroke();
          }
          // selection ring (slightly different from hover — thinner, persists)
          if (n.id === selectedSlug && n.id !== hoveredId) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
          // node body
          ctx.beginPath();
          ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = n.id === hoveredId ? "#ffffff" : n.color;
          ctx.fill();
          if (opacity < 1) ctx.globalAlpha = 1;
          // Labels are drawn in onRenderFramePost so they're always on top.
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D, globalScale: number) => {
          // Draw labels AFTER all nodes so they're never occluded.
          for (const node of data.nodes) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const n = node as any;
            if (n.id === hoveredId || n.id === selectedSlug) {
              const r = n.val || 4;
              // Constant label size: 11px screen pixels regardless of zoom
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px sans-serif`;
              const text = n.name || n.id;
              const textW = ctx.measureText(text).width;
              const pad = 3 / globalScale;
              const tx = n.x + r + pad;
              const ty = n.y + pad;
              ctx.fillStyle = "rgba(0,0,0,0.8)";
              ctx.beginPath();
              ctx.roundRect(tx - pad, ty - fontSize + pad / 3, textW + pad * 2, fontSize + pad * 1.3, pad);
              ctx.fill();
              ctx.fillStyle = "rgba(255,255,255,0.95)";
              ctx.fillText(text, tx, ty);
            }
          }
        }}
        onNodeHover={(node: unknown) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setHoveredId((node as any)?.id || null);
        }}
        onEngineStop={() => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fg = fgRef.current as any;
          if (fg?.zoomToFit && !fg._montyInitialFit) {
            fg.zoomToFit(400, 40);
            fg._montyInitialFit = true;
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
