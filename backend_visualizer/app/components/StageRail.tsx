"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

const STAGES = [
  "waiting_for_note",
  "reassessing_student",
  "updating_profile",
  "enriching_knowledge",
  "writing_alert",
  "cycle_complete",
  "researching_edges",
  "research_edge_found",
];

export function StageRail() {
  const [stage, setStage] = useState<string>("waiting_for_note");
  const [student, setStudent] = useState<string>("");
  const [progressPct, setProgressPct] = useState(0);

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, stats] = await Promise.all([
          api.demoOverview() as Promise<{ runtime?: Record<string, string> }>,
          api.ingestionStats(),
        ]);
        const rt = overview?.runtime || {};
        setStage(rt.current_stage || "waiting_for_note");
        setStudent(rt.current_student || "");
        // For enriching_knowledge, prefer query-level progress; otherwise use stage_progress
        const s = rt.current_stage || "";
        const qp = (stats as unknown as Record<string, string>).enrich_query_progress || "";
        const sp = (stats as unknown as Record<string, string>).stage_progress || "";
        const prog = (s === "enriching_knowledge" && qp) ? qp : sp;
        const parts = prog.split("/");
        if (parts.length === 2 && parseInt(parts[1]) > 0) {
          setProgressPct((parseInt(parts[0]) / parseInt(parts[1])) * 100);
        } else {
          setProgressPct(0);
        }
      } catch {}
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);

  const activeIdx = STAGES.indexOf(stage);
  const displayStages = activeIdx === -1 && stage ? [...STAGES, stage] : STAGES;
  const activeDisplayIdx = displayStages.indexOf(stage);

  return (
    <div className="h-12 flex items-center justify-between px-4 bg-zinc-950 border-y border-white/10 font-mono text-[11px] shrink-0 overflow-x-auto">
      {displayStages.map((s, idx) => {
        const active = idx === activeDisplayIdx;
        const passed = activeDisplayIdx > idx;
        return (
          <div key={s} className="flex items-center gap-1.5 shrink-0">
            <div className="flex flex-col">
              <div className={`flex items-center gap-1.5 ${
                active ? "text-white" : passed ? "text-white/40" : "text-white/30"
              }`}>
                <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${
                  active
                    ? "bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse"
                    : passed ? "bg-emerald-700" : "bg-zinc-700"
                }`} />
                <span className="whitespace-nowrap">
                  {s.replace(/_/g, " ")}
                  {active && student ? ` · ${student}` : ""}
                </span>
              </div>
              {/* Progress bar only under the currently active stage */}
              {active && stage !== "waiting_for_note" && stage !== "cycle_complete" && stage !== "research_edge_found" && (
                <div className="h-[3px] bg-white/10 rounded-full overflow-hidden mt-0.5 ml-3">
                  <div
                    className="h-full bg-emerald-400 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${progressPct > 0 ? Math.max(8, progressPct) : 100}%` }}
                  />
                </div>
              )}
            </div>
            {idx < displayStages.length - 1 && (
              <span className="mx-1 text-white/10">›</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
