"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { forceX, forceY } from "d3-force";
import { api, type StudentIncident, type BehavioralNode } from "../lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
}) as unknown as React.ComponentType<Record<string, unknown>>;

// Per-persona color palettes — maximally distinct hue families.
// Each type within a persona uses different lightness/saturation for contrast.
const PERSONA_PALETTES: Record<string, Record<string, string>> = {
  "Arjun Nair": {
    setting_event: "#FF4444",   // bright red
    antecedent: "#FF8866",      // coral
    behavior: "#CC2200",        // dark red
    function: "#FF6633",        // red-orange
    brain_state: "#FF2266",     // crimson
    response: "#FFAA88",        // peach
    protective_factor: "#CC5544", // brick
  },
  "Diya Malhotra": {
    setting_event: "#7C4DFF",   // electric purple
    antecedent: "#B388FF",      // light purple
    behavior: "#5500CC",        // deep purple
    function: "#9C6AFF",        // medium purple
    brain_state: "#6200EA",     // indigo-purple
    response: "#D1C4E9",        // pale lilac
    protective_factor: "#8855DD", // plum
  },
  "Kiaan Gupta": {
    setting_event: "#00E5FF",   // electric cyan
    antecedent: "#00BFA5",      // teal
    behavior: "#1DE9B6",        // mint green
    function: "#00B8D4",        // dark cyan
    brain_state: "#18FFFF",     // bright cyan
    response: "#64FFDA",        // aqua
    protective_factor: "#26A69A", // deep teal
  },
  "Mira Shah": {
    setting_event: "#FFAB00",   // vivid amber
    antecedent: "#FFD740",      // bright gold
    behavior: "#FF8F00",        // deep orange
    function: "#FFC400",        // sunflower
    brain_state: "#FFEA00",     // yellow
    response: "#FFD180",        // light peach
    protective_factor: "#FF6D00", // tangerine
  },
  "Saanvi Verma": {
    setting_event: "#FF4081",   // hot pink
    antecedent: "#F50057",      // deep pink
    behavior: "#FF80AB",        // light pink
    function: "#E040FB",        // purple-pink
    brain_state: "#D500F9",     // vivid magenta
    response: "#FF8A80",        // salmon pink
    protective_factor: "#EA80FC", // orchid
  },
};

const NODE_TYPE_LABELS: Record<string, string> = {
  setting_event: "Setting Event",
  antecedent: "Antecedent",
  behavior: "Behavior",
  function: "Function",
  brain_state: "Brain State",
  response: "Response",
  protective_factor: "Protective Factor",
};

// Fallback palette for unknown students
const DEFAULT_PALETTE: Record<string, string> = {
  setting_event: "#00D8FF",
  antecedent: "#BC8CFF",
  behavior: "#FFA657",
  function: "#FF7EB6",
  brain_state: "#79C0FF",
  response: "#3FB950",
  protective_factor: "#94a3b8",
};

function getPalette(name: string): Record<string, string> {
  return PERSONA_PALETTES[name] || DEFAULT_PALETTE;
}

function pathToType(refPath: string): string {
  const parts = refPath.split("/");
  const folder = parts.length >= 2 ? parts[parts.length - 2] : "";
  return folder.replace(/s$/, "");
}

export function StudentGraphPanel({
  studentName,
  incidents,
  highlightSlug,
  onSelectNode,
}: {
  studentName: string;
  incidents: StudentIncident[];
  highlightSlug: string | null;
  onSelectNode: (slug: string | null) => void;
}) {
  const [behavioralIndex, setBehavioralIndex] = useState<
    Record<string, BehavioralNode>
  >({});
  const [degraded, setDegraded] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showLegend, setShowLegend] = useState(false);
  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 800, h: 300 });
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeObjRef = useRef<Map<string, any>>(new Map());
  const prevIncidentIdsRef = useRef<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const fgRef = useRef<unknown>(null);

  const palette = getPalette(studentName);

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

  // Fetch behavioral index periodically
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const bg = await api.behavioralGraph(1);
        if (stop) return;
        const idx: Record<string, BehavioralNode> = {};
        for (const n of bg.nodes || []) idx[n.slug] = n;
        setBehavioralIndex(idx);
        setDegraded(false);
      } catch {
        if (!stop) setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 4000);
    return () => { stop = true; clearInterval(i); };
  }, []);

  // Build graph data — structural diff to avoid reheat jitter
  useEffect(() => {
    const touchCounts = new Map<string, number>();
    const coocCounts = new Map<string, number>();
    for (const inc of incidents) {
      const refs = inc.behavioral_ref_slugs || [];
      for (const r of refs) touchCounts.set(r, (touchCounts.get(r) || 0) + 1);
      for (let i = 0; i < refs.length; i++) {
        for (let j = i + 1; j < refs.length; j++) {
          const [a, b] = [refs[i], refs[j]].sort();
          const key = `${a}||${b}`;
          coocCounts.set(key, (coocCounts.get(key) || 0) + 1);
        }
      }
    }

    const nodeMap = nodeObjRef.current;
    const newIds = new Set<string>();
    let hasNewNodes = false;
    let hasRemovedNodes = false;

    for (const [refPath, count] of touchCounts) {
      newIds.add(refPath);
      const slug = refPath.split("/").pop() || refPath;
      const fromIndex = behavioralIndex[slug];
      const type = fromIndex?.type || pathToType(refPath);
      const title = fromIndex?.title || slug;
      const val = Math.max(3, Math.log2(1 + count) * 5);
      const color = palette[type] || palette.behavior || "#6b7280";

      const existing = nodeMap.get(refPath);
      if (existing) {
        existing.val = val;
        existing.count = count;
        existing.name = title;
        existing.type = type;
        existing.slug = slug;
        existing.color = color;
      } else {
        const existingNodes = Array.from(nodeMap.values());
        const neighbor = existingNodes.length > 0
          ? existingNodes[Math.floor(Math.random() * existingNodes.length)]
          : null;
        nodeMap.set(refPath, {
          id: refPath,
          slug,
          name: title,
          type,
          count,
          val,
          color,
          x: neighbor ? neighbor.x + (Math.random() - 0.5) * 40 : undefined,
          y: neighbor ? neighbor.y + (Math.random() - 0.5) * 40 : undefined,
          _enterTime: Date.now(),
        });
        hasNewNodes = true;
      }
    }

    for (const key of nodeMap.keys()) {
      if (!newIds.has(key)) { nodeMap.delete(key); hasRemovedNodes = true; }
    }

    const incIdKey = incidents.map((i) => i.id).sort().join(",");
    const structuralChange = incIdKey !== prevIncidentIdsRef.current;

    if (structuralChange || hasNewNodes || hasRemovedNodes || graphData.nodes.length === 0) {
      prevIncidentIdsRef.current = incIdKey;
      const now = Date.now();

      const links: Record<string, unknown>[] = [];
      for (const [key, count] of coocCounts) {
        const [a, b] = key.split("||");
        if (!nodeMap.has(a) || !nodeMap.has(b)) continue;
        links.push({
          source: a,
          target: b,
          width: Math.max(0.4, Math.log2(1 + count) * 1.2),
          count,
          color: "rgba(255,255,255,0.35)",
          _enterTime: now,
        });
      }

      setGraphData({ nodes: Array.from(nodeMap.values()), links });
    }
  }, [incidents, behavioralIndex, palette]); // eslint-disable-line react-hooks/exhaustive-deps

  const data = graphData;
  const isEmpty = data.nodes.length === 0;

  // Collect which node types are present for the legend
  const presentTypes = new Set(data.nodes.map((n: { type?: string }) => n.type || ""));

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full bg-zinc-950 overflow-hidden"
      onMouseEnter={() => setShowLegend(true)}
      onMouseLeave={() => setShowLegend(false)}
    >
      {/* Info overlay */}
      <div className="absolute top-2 left-2 z-10 bg-black/70 rounded p-2 text-[11px] text-white/80 font-mono border border-white/10 max-w-xs">
        <div className="font-semibold mb-1 text-white">
          {studentName}
          <span className="text-white/40"> · subgraph</span>
        </div>
        <div className="text-white/50">
          {incidents.length} incidents · {data.nodes.length} nodes touched
        </div>
      </div>

      {/* Hover legend — shows node type colors for this persona */}
      {showLegend && presentTypes.size > 0 && (
        <div className="absolute bottom-2 left-2 z-10 bg-black/80 rounded p-2 text-[9px] font-mono border border-white/10 backdrop-blur-sm">
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {Object.entries(palette).map(([type, color]) => {
              if (!presentTypes.has(type)) return null;
              return (
                <div key={type} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                  <span className="text-white/60">{NODE_TYPE_LABELS[type] || type}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {degraded && (
        <div className="absolute top-14 left-2 z-10 text-[10px] text-amber-300/80 font-mono bg-amber-950/40 border border-amber-500/20 rounded px-2 py-1">
          data unreachable
        </div>
      )}
      {isEmpty && !degraded && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-white/40 font-mono text-xs max-w-sm px-4">
            No behavioral nodes for {studentName} yet.
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
            const charge = fg.d3Force("charge");
            if (charge) charge.strength(-30);
            fg.d3Force("x", forceX());
            fg.d3Force("y", forceY());
            fg._montyForcesTuned = true;
          }
        }}
        linkWidth={(l: unknown) => Math.max(0.8, (l as { width: number }).width)}
        linkColor={(l: unknown) => (l as { color: string }).color}
        nodeCanvasObject={(
          node: unknown,
          ctx: CanvasRenderingContext2D,
          globalScale: number,
        ) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const n = node as any;
          const r = n.val;
          const isHighlighted =
            highlightSlug && (n.slug === highlightSlug || n.id.endsWith(highlightSlug));
          // Fade-in: 0→1 over 100ms
          const age = n._enterTime ? Date.now() - n._enterTime : 1000;
          const opacity = Math.min(1, age / 100);
          if (opacity < 1) ctx.globalAlpha = opacity;
          // hover ring
          if (n.id === hoveredId) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
            ctx.strokeStyle = "rgba(255,255,255,0.9)";
            ctx.lineWidth = 2;
            ctx.stroke();
          } else if (isHighlighted) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(255,255,255,0.25)";
            ctx.fill();
          }
          ctx.beginPath();
          ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = n.id === hoveredId ? "#ffffff" : isHighlighted ? "white" : n.color;
          ctx.fill();
          if (opacity < 1) ctx.globalAlpha = 1;
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D, globalScale: number) => {
          for (const node of data.nodes) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const n = node as any;
            const isHighlighted = highlightSlug && (n.slug === highlightSlug || n.id?.endsWith?.(highlightSlug));
            if (n.id === hoveredId || isHighlighted) {
              const r = n.val || 4;
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px sans-serif`;
              const text = (n.name || n.id) as string;
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
            fg.zoomToFit(300, 20);
            fg._montyInitialFit = true;
          }
        }}
        onNodeClick={(node: unknown) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const n = node as any;
          onSelectNode(n.slug === highlightSlug ? null : n.slug);
        }}
      />
    </div>
  );
}
