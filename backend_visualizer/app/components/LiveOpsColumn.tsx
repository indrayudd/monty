"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function LiveOpsColumn() {
  const [status, setStatus] = useState<Record<string, string>>({});
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, curiosity] = await Promise.all([
          api.demoOverview() as Promise<{ runtime?: Record<string, string> }>,
          api.curiosityEvents(5),
        ]);
        setStatus(overview?.runtime || {});
        setEvents(curiosity?.events || []);
      } catch {}
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);

  const stage = status.current_stage || "idle";
  const student = status.current_student || "—";

  return (
    <div className="w-[332px] shrink-0 rounded bg-zinc-900/80 border border-white/10 p-3 flex flex-col gap-4 overflow-y-auto">
      {/* CYCLE STAGE */}
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

      {/* STUDENT FOCUS */}
      <section>
        <h3 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">Student Focus</h3>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <span className="text-sm text-white font-medium">{student}</span>
        </div>
      </section>

      {/* RESEARCH QUEUE */}
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
  );
}
