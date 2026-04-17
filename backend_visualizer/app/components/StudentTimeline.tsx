"use client";
import { useEffect, useState } from "react";
import { api, type StudentIncident, type Persona } from "../lib/api";
import { StudentGraphPanel } from "./StudentGraphPanel";
import { StudentResearchPanel } from "./StudentResearchPanel";

const SEVERITY_COLORS: Record<string, string> = {
  red: "bg-rose-500",
  yellow: "bg-amber-400",
  green: "bg-emerald-500",
  "": "bg-zinc-600",
};

type View = "timeline" | "graph" | "research";

export function StudentTimeline({
  highlightSlug,
  onOpenIncident,
  onSelectBehavioralNode,
}: {
  highlightSlug: string | null;
  onOpenIncident: (incident: StudentIncident) => void;
  onSelectBehavioralNode: (slug: string | null) => void;
}) {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [active, setActive] = useState<string | null>(null);
  // Pre-cache per-student incidents so switching is instant.
  const [studentData, setStudentData] = useState<
    Record<string, StudentIncident[]>
  >({});
  const [view, setView] = useState<View>("timeline");

  useEffect(() => {
    api
      .personas()
      .then((r) => {
        setPersonas(r.personas || []);
        if (!active && r.personas?.length) {
          setActive(r.personas[0].name);
        }
      })
      .catch(() => setPersonas([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll ALL students in parallel every 2s so all five are warm. Switching
  // personas then serves cached data immediately; the next tick refreshes.
  useEffect(() => {
    if (personas.length === 0) return;
    let stop = false;
    const tick = async () => {
      try {
        const results = await Promise.allSettled(
          personas.map((p) => api.studentGraph(p.name)),
        );
        if (stop) return;
        setStudentData((prev) => {
          const next = { ...prev };
          for (let i = 0; i < personas.length; i++) {
            const r = results[i];
            if (r.status === "fulfilled") {
              next[personas[i].name] = r.value.incidents || [];
            }
          }
          return next;
        });
      } catch {
        // keep last known state
      }
    };
    tick();
    const interval = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(interval);
    };
  }, [personas]);

  const incidents: StudentIncident[] = active ? studentData[active] || [] : [];

  const renderTabs = () => (
    <div className="flex gap-1 ml-auto shrink-0">
      {(
        [
          ["timeline", "Timeline"],
          ["graph", "Graph"],
          ["research", "Research"],
        ] as const
      ).map(([v, label]) => (
        <button
          key={v}
          onClick={() => setView(v)}
          className={`px-2.5 py-1 text-[11px] font-mono rounded transition ${
            view === v
              ? "bg-white/10 text-white"
              : "text-white/50 hover:text-white"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="flex items-center gap-2 p-2 overflow-x-auto border-b border-white/5">
        {personas.length === 0 && (
          <div className="text-white/30 text-xs font-mono px-2 py-1.5">
            No personas loaded — check /api/personas.
          </div>
        )}
        {personas.map((p) => (
          <button
            key={p.name}
            onClick={() => setActive(p.name)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded font-mono text-xs border transition shrink-0 ${
              active === p.name
                ? "border-white bg-white/5 shadow-[0_0_0_1px_rgba(255,255,255,0.1)]"
                : "border-white/10 hover:border-white/30"
            }`}
          >
            <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-white text-[11px]">
              {p.name.charAt(0)}
            </span>
            <span className="text-white">{p.name}</span>
            <span className="text-white/40">·</span>
            <span className="text-white/60">{p.age_band}</span>
          </button>
        ))}
        {renderTabs()}
      </div>
      {view === "graph" && active && (
        <div className="flex-1 min-h-0">
          <StudentGraphPanel
            studentName={active}
            incidents={incidents}
            highlightSlug={highlightSlug}
            onSelectNode={onSelectBehavioralNode}
          />
        </div>
      )}
      {view === "research" && active && (
        <div className="flex-1 min-h-0">
          <StudentResearchPanel studentName={active} />
        </div>
      )}
      {view === "timeline" && (
      <div className="flex-1 overflow-x-auto overflow-y-hidden flex gap-2 p-3 min-h-0">
        {active && incidents.length === 0 && (
          <div className="text-white/40 text-sm self-center font-mono w-full text-center">
            No observations yet for {active} — try God Mode → Inject Note.
          </div>
        )}
        {[...incidents].reverse().map((inc) => {
          const highlighted =
            !!highlightSlug &&
            inc.behavioral_ref_slugs.some((s) => s.endsWith(highlightSlug));
          const ago = (() => {
            const t = new Date(inc.ingested_at).getTime();
            const s = Math.max(0, (Date.now() - t) / 1000);
            return s < 60
              ? `${Math.round(s)}s ago`
              : s < 3600
                ? `${Math.round(s / 60)}m ago`
                : `${Math.round(s / 3600)}h ago`;
          })();
          return (
            <button
              key={inc.id}
              onClick={() => onOpenIncident(inc)}
              className={`shrink-0 w-56 text-left p-3 rounded border transition ${
                highlighted
                  ? "border-white shadow-[0_0_12px_rgba(255,255,255,0.5)]"
                  : "border-white/10 hover:border-white/30"
              } bg-zinc-900`}
            >
              <div className="flex items-center justify-between font-mono text-[10px] text-white/50">
                <span>{ago}</span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    SEVERITY_COLORS[inc.severity || ""] || "bg-zinc-600"
                  }`}
                />
              </div>
              <div className="mt-2 text-xs text-white/80 font-mono">
                note #{inc.note_id}
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {inc.behavioral_ref_slugs.slice(0, 6).map((s) => (
                  <span
                    key={s}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/60 font-mono"
                  >
                    {s.split("/").slice(-2, -1)[0] || s}
                  </span>
                ))}
                {inc.behavioral_ref_slugs.length > 6 && (
                  <span className="text-[9px] text-white/30">
                    +{inc.behavioral_ref_slugs.length - 6}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
      )}
    </div>
  );
}
