"use client";
import { useEffect, useState } from "react";
import { api, type CuriosityEvent } from "../lib/api";

export function CuriosityEventsStream() {
  const [events, setEvents] = useState<CuriosityEvent[]>([]);
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.curiosityEvents(50);
        setEvents(r.events || []);
        setDegraded(false);
      } catch {
        setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);

  return (
    <section className="bg-zinc-950 border border-white/10 rounded p-3 font-mono text-xs">
      <div className="flex items-center justify-between mb-2">
        <div className="text-white/50">Curiosity events</div>
        <div className="text-white/30 text-[10px]">
          {events.length} loaded
        </div>
      </div>
      {degraded && (
        <div className="text-amber-300/80 text-[10px] mb-2">
          ⚠ /api/curiosity/events unreachable
        </div>
      )}
      {!degraded && events.length === 0 && (
        <div className="text-white/30">
          (no curiosity evaluations yet — the agent will start emitting these
          once nodes begin attracting attention)
        </div>
      )}
      <div className="space-y-1">
        {events.map((ev) => (
          <div
            key={ev.id}
            className="grid grid-cols-12 gap-2 items-center text-white/80 hover:bg-white/5 rounded px-1"
          >
            <span className="col-span-2 text-white/40">
              {new Date(ev.fired_at).toLocaleTimeString()}
            </span>
            <span
              className={`col-span-1 ${
                ev.triggered_research ? "text-emerald-400" : "text-white/30"
              }`}
            >
              {ev.triggered_research ? "fire" : "skip"}
            </span>
            <span className="col-span-4 truncate" title={ev.node_slug}>
              {ev.node_slug}
            </span>
            <span className="col-span-1 text-right">
              {ev.curiosity_score.toFixed(2)}
            </span>
            <span className="col-span-4 flex items-end gap-0.5 h-4">
              {["novelty","recurrence_gap","cross_student","surprise","severity_weight","recency"].map(k => {
                const v = Math.max(0, Math.min(1, (ev.factors?.[k] as number) ?? 0));
                return (
                  <span
                    key={k}
                    title={`${k}: ${v.toFixed(2)}`}
                    className="w-2 bg-white/70 hover:bg-white rounded-t"
                    style={{ height: `${Math.max(2, v * 100)}%` }}
                  />
                );
              })}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
