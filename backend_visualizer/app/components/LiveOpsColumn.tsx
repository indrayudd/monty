"use client";
import { useEffect, useState } from "react";
import { api, type Persona, type StudentIncident } from "../lib/api";
import { StudentGraphPanel } from "./StudentGraphPanel";
import { StudentResearchPanel } from "./StudentResearchPanel";

type OpsView = "status" | "graph" | "research";

export function LiveOpsColumn({
  highlightSlug,
  onSelectNode,
}: {
  highlightSlug: string | null;
  onSelectNode: (slug: string | null) => void;
}) {
  const [status, setStatus] = useState<Record<string, string>>({});
  const [events, setEvents] = useState<{ id?: number; node_slug: string; curiosity_score: number; triggered_research: boolean }[]>([]);
  const [view, setView] = useState<OpsView>("status");
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [activeStudent, setActiveStudent] = useState<string | null>(null);
  const [studentData, setStudentData] = useState<Record<string, StudentIncident[]>>({});

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, curiosity, personaRes] = await Promise.all([
          api.demoOverview() as Promise<{ runtime?: Record<string, string> }>,
          api.curiosityEvents(5),
          api.personas(),
        ]);
        setStatus(overview?.runtime || {});
        setEvents(curiosity?.events || []);
        const ps = personaRes.personas || [];
        setPersonas(prev => prev.length === ps.length ? prev : ps);
        setActiveStudent(prev => prev || (ps.length ? ps[0].name : null));
      } catch {}
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll student incidents for graph view
  useEffect(() => {
    if (!activeStudent || view !== "graph") return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.studentGraph(activeStudent);
        if (!stop) setStudentData(prev => ({ ...prev, [activeStudent]: r.incidents || [] }));
      } catch {}
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => { stop = true; clearInterval(i); };
  }, [activeStudent, view]);

  const stage = status.current_stage || "idle";
  const student = status.current_student || "—";
  const incidents = activeStudent ? studentData[activeStudent] || [] : [];

  return (
    <div className="w-[332px] shrink-0 rounded bg-zinc-900/80 border border-white/10 flex flex-col overflow-hidden">
      {/* View tabs */}
      <div className="flex border-b border-white/10 shrink-0">
        {([["status", "Status"], ["graph", "Graph"], ["research", "Research"]] as const).map(([v, label]) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`flex-1 text-[10px] font-mono py-1.5 transition-colors ${
              view === v ? "bg-white/10 text-white" : "text-white/40 hover:text-white/70 hover:bg-white/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Status view */}
      {view === "status" && (
        <div className="p-3 flex flex-col gap-4 overflow-y-auto flex-1">
          <section>
            <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Cycle Stage</h3>
            <div className="text-sm font-semibold text-white">{stage.replace(/_/g, " ")}</div>
            <div className="text-xs text-white/60 mt-1">&gt; {student}</div>
            <div className="flex flex-wrap gap-1 mt-2">
              {["reassessing", "will_enrich", "generating_alert", "reset", "explore", "student", "notes"].map(k => (
                <span key={k} className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                  stage.includes(k) ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-white/30"
                }`}>{k}</span>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Student Focus</h3>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="text-sm text-white font-medium">{student}</span>
            </div>
          </section>

          <section>
            <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Research Queue</h3>
            {events.length === 0 && (
              <div className="text-[10px] text-white/30 font-mono">no research queued</div>
            )}
            {events.map((ev, i) => (
              <div key={ev.id || i} className="flex items-center justify-between text-[10px] font-mono py-1 border-b border-white/5 last:border-0">
                <span className="text-white/70 truncate max-w-[200px]">{ev.node_slug}</span>
                <span className={`px-1.5 py-0.5 rounded ${
                  ev.triggered_research ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-white/40"
                }`}>
                  {ev.curiosity_score?.toFixed(2) || "—"}
                </span>
              </div>
            ))}
          </section>
        </div>
      )}

      {/* Graph view */}
      {view === "graph" && (
        <div className="flex flex-col flex-1 min-h-0">
          <div className="flex gap-1 p-2 overflow-x-auto shrink-0 border-b border-white/5">
            {personas.map(p => (
              <button
                key={p.name}
                onClick={() => setActiveStudent(p.name)}
                className={`text-[9px] font-mono px-2 py-1 rounded shrink-0 transition ${
                  activeStudent === p.name ? "bg-white/10 text-white" : "text-white/40 hover:text-white"
                }`}
              >
                {p.name.split(" ")[0]}
              </button>
            ))}
          </div>
          <div className="flex-1 min-h-0">
            {activeStudent && (
              <StudentGraphPanel
                studentName={activeStudent}
                incidents={incidents}
                highlightSlug={highlightSlug}
                onSelectNode={onSelectNode}
              />
            )}
          </div>
        </div>
      )}

      {/* Research view */}
      {view === "research" && (
        <div className="flex flex-col flex-1 min-h-0">
          <div className="flex gap-1 p-2 overflow-x-auto shrink-0 border-b border-white/5">
            {personas.map(p => (
              <button
                key={p.name}
                onClick={() => setActiveStudent(p.name)}
                className={`text-[9px] font-mono px-2 py-1 rounded shrink-0 transition ${
                  activeStudent === p.name ? "bg-white/10 text-white" : "text-white/40 hover:text-white"
                }`}
              >
                {p.name.split(" ")[0]}
              </button>
            ))}
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto">
            {activeStudent && <StudentResearchPanel studentName={activeStudent} />}
          </div>
        </div>
      )}
    </div>
  );
}
