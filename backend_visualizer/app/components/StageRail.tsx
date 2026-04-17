"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

const STAGES = [
  "waiting_for_note",
  "ingesting_note",
  "reassessing_student",
  "updating_profile",
  "enriching_knowledge",
  "writing_alert",
  "cycle_complete",
];

export function StageRail() {
  const [stage, setStage] = useState<string>("waiting_for_note");
  const [student, setStudent] = useState<string>("");

  useEffect(() => {
    const tick = async () => {
      try {
        // Read from /api/agent/status which reflects the real agent_runtime_state
        // rows written by the agent loop — works whether the demo was "started"
        // via God Mode or the loop was launched from CLI.
        const o = (await api.demoOverview()) as {
          runtime?: Record<string, string>;
        };
        const rt = o?.runtime || {};
        setStage(rt.current_stage || "waiting_for_note");
        setStudent(rt.current_student || "");
      } catch {
        /* keep last */
      }
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);

  const activeIdx = STAGES.indexOf(stage);

  return (
    <div className="h-10 flex items-center justify-between px-4 bg-zinc-950 border-y border-white/10 font-mono text-[11px] shrink-0">
      {STAGES.map((s, idx) => {
        const active = idx === activeIdx;
        const passed = activeIdx > idx;
        return (
          <div
            key={s}
            className={`flex items-center gap-1.5 ${
              active
                ? "text-white"
                : passed
                  ? "text-white/40"
                  : "text-white/30"
            }`}
          >
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                active
                  ? "bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse"
                  : passed
                    ? "bg-emerald-700"
                    : "bg-zinc-700"
              }`}
            />
            <span className="whitespace-nowrap">
              {s.replace(/_/g, " ")}
              {active && student ? ` · ${student}` : ""}
            </span>
            {idx < STAGES.length - 1 && (
              <span className="mx-1 text-white/10">›</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
