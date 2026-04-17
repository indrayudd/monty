"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { forceX, forceY } from "d3-force";
import { api, type StudentIncident, type BehavioralNode } from "../lib/api";

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
  protective_factor: "#94a3b8",
};

function pathToType(refPath: string): string {
  // e.g. "behavioral/antecedents/peer-takes-material" -> "antecedent"
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
  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 800, h: 300 });
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Preserve node identity across polls AND across student switches so the
  // force layout keeps positions for shared nodes. Unreferenced nodes drop
  // naturally when they're no longer in the touch count.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeObjRef = useRef<Map<string, any>>(new Map());
  const fgRef = useRef<unknown>(null);

  // Fetch the behavioral index (for node types/titles) periodically.
  // Incidents come in via props from the parent's per-student pre-cache.
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
    const i = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(i);
    };
  }, []);

  // Track previous structural state to avoid force-graph reheat on property-only polls.
  const prevIncidentIdsRef = useRef<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const prevGraphDataRef = useRef<{ nodes: any[]; links: any[] } | null>(null);

  const data = useMemo(() => {
    // How many of this student's incidents touched each behavioral ref
    const touchCounts = new Map<string, number>();
    // Co-occurrence counts for pairs within the same incident
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

    // Check if the incident set structurally changed (new/removed incidents).
    // If not, mutate node properties in place and return the SAME graphData
    // reference so force-graph doesn't reheat the simulation.
    const incIdKey = incidents.map((i) => i.id).sort().join(",");
    const structuralChange = incIdKey !== prevIncidentIdsRef.current;

    // Always mutate existing node properties in place
    const prev = nodeObjRef.current;
    for (const [refPath, count] of touchCounts) {
      const existing = prev.get(refPath);
      if (existing) {
        const slug = refPath.split("/").pop() || refPath;
        const fromIndex = behavioralIndex[slug];
        existing.val = Math.max(3, Math.log2(1 + count) * 5);
        existing.count = count;
        existing.name = fromIndex?.title || slug;
        existing.type = fromIndex?.type || pathToType(refPath);
        existing.slug = slug;
        existing.color = TYPE_COLORS[existing.type as string] || "#6b7280";
      }
    }

    // If no structural change, return previous graphData ref (no reheat)
    if (!structuralChange && prevGraphDataRef.current) {
      return prevGraphDataRef.current;
    }
    prevIncidentIdsRef.current = incIdKey;

    const next = new Map<string, Record<string, unknown>>();
    for (const [refPath, count] of touchCounts) {
      const slug = refPath.split("/").pop() || refPath;
      const fromIndex = behavioralIndex[slug];
      const type = fromIndex?.type || pathToType(refPath);
      const title = fromIndex?.title || slug;
      const val = Math.max(3, Math.log2(1 + count) * 5);
      const existing = prev.get(refPath);
      if (existing) {
        next.set(refPath, existing);
      } else {
        next.set(refPath, {
          id: refPath,
          slug,
          name: title,
          type,
          count,
          val,
          color: TYPE_COLORS[type] || "#6b7280",
        });
      }
    }
    nodeObjRef.current = next;

    const links: Record<string, unknown>[] = [];
    for (const [key, count] of coocCounts) {
      const [a, b] = key.split("||");
      if (!next.has(a) || !next.has(b)) continue;
      links.push({
        source: a,
        target: b,
        width: Math.max(0.4, Math.log2(1 + count) * 1.2),
        count,
        color: "rgba(255,255,255,0.22)",
      });
    }

    const result = { nodes: Array.from(next.values()), links };
    prevGraphDataRef.current = result;
    return result;
  }, [incidents, behavioralIndex]);

  const isEmpty = data.nodes.length === 0;

  return (
    <div ref={containerRef} className="relative h-full w-full bg-zinc-950 overflow-hidden">
      <div className="absolute top-2 left-2 z-10 bg-black/70 rounded p-2 text-[11px] text-white/80 font-mono border border-white/10 max-w-xs">
        <div className="font-semibold mb-1 text-white">
          {studentName}
          <span className="text-white/40"> · subgraph</span>
        </div>
        <div className="text-white/50">
          {incidents.length} incidents · {data.nodes.length} nodes touched ·
          node size = this student&apos;s touch count
        </div>
      </div>
      {degraded && (
        <div className="absolute top-14 left-2 z-10 text-[10px] text-amber-300/80 font-mono bg-amber-950/40 border border-amber-500/20 rounded px-2 py-1">
          ⚠ data unreachable — last render retained
        </div>
      )}
      {isEmpty && !degraded && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-white/40 font-mono text-xs max-w-sm px-4">
            No behavioral nodes touched by {studentName} yet. Wait for the
            agent loop to process incoming notes, or inject a few via God
            Mode.
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
        warmupTicks={80}
        cooldownTicks={60}
        d3AlphaDecay={0.1}
        d3VelocityDecay={0.55}
        onEngineTick={() => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fg = fgRef.current as any;
          if (!fg || fg._montyForcesTuned) return;
          if (fg.d3Force) {
            const charge = fg.d3Force("charge");
            if (charge) charge.strength(-45).distanceMax(260);
            fg.d3Force("x", forceX(0).strength(0.06));
            fg.d3Force("y", forceY(0).strength(0.06));
            fg._montyForcesTuned = true;
          }
        }}
        linkWidth={(l: unknown) => (l as { width: number }).width}
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
          if (isHighlighted) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(255,255,255,0.25)";
            ctx.fill();
          }
          ctx.beginPath();
          ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = isHighlighted ? "white" : n.color;
          ctx.fill();
          // Labels drawn in onRenderFramePost so they're always on top.
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D, globalScale: number) => {
          for (const node of data.nodes) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const n = node as any;
            const isHighlighted = highlightSlug && (n.slug === highlightSlug || n.id?.endsWith?.(highlightSlug));
            if (n.id === hoveredId || isHighlighted) {
              const r = n.val || 4;
              const fontSize = Math.min(12, Math.max(9, 10 / globalScale));
              ctx.font = `${fontSize}px sans-serif`;
              const text = (n.name || n.id) as string;
              const textW = ctx.measureText(text).width;
              const tx = n.x + r + 4;
              const ty = n.y + 3;
              ctx.fillStyle = "rgba(0,0,0,0.8)";
              ctx.beginPath();
              ctx.roundRect(tx - 3, ty - fontSize + 1, textW + 6, fontSize + 4, 3);
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
          // Auto-zoom to fit all nodes on FIRST settle only. Subsequent
          // engine stops (from data polls) must not override the user's
          // pan/zoom.
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fg = fgRef.current as any;
          if (fg?.zoomToFit && !fg._montyInitialFit) {
            fg.zoomToFit(400, 30);
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
