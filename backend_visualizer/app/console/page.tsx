"use client";
import { useEffect, useState } from "react";
import { CuriosityEventsStream } from "../components/CuriosityEventsStream";
import { api } from "../lib/api";

type OverviewRuntime = {
  mode?: string;
  current_stage?: string;
  current_student?: string;
  current_note_id?: number | null;
  last_cycle_completed_at?: string;
  [k: string]: unknown;
};

export default function ConsolePage() {
  const [overview, setOverview] = useState<{
    runtime?: OverviewRuntime;
  } | null>(null);
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = (await api.demoOverview()) as {
          runtime?: OverviewRuntime;
        };
        setOverview(r);
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
    <div className="h-[calc(100vh-3rem)] p-4 space-y-4 overflow-y-auto">
      <section className="bg-zinc-950 border border-white/10 rounded p-3 font-mono text-xs text-white/80">
        <div className="flex items-center justify-between mb-2">
          <div className="text-white/50">Agent status</div>
          {degraded && (
            <div className="text-amber-300/80 text-[10px]">
              ⚠ /api/demo/overview unreachable
            </div>
          )}
        </div>
        {overview?.runtime ? (
          <pre className="whitespace-pre-wrap text-white/80">
            {JSON.stringify(overview.runtime, null, 2)}
          </pre>
        ) : (
          <div className="text-white/30">(no runtime snapshot yet)</div>
        )}
      </section>
      <CuriosityEventsStream />
    </div>
  );
}
