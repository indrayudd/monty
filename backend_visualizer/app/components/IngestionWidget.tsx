"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Stats = {
  total_notes: number;
  processed: number;
  backlog: number;
  stage: string;
  current_student: string;
  enrich_progress: string;
};

export function IngestionWidget() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.ingestionStats();
        setStats(r as Stats);
      } catch {
        /* offline */
      }
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, []);

  if (!stats) return null;

  const hasBacklog = stats.backlog > 5;
  const isEnriching = stats.stage === "enriching_knowledge";
  const enrichParts = stats.enrich_progress?.split("/") || [];
  const enrichPct = enrichParts.length === 2
    ? (parseInt(enrichParts[0]) / parseInt(enrichParts[1])) * 100
    : 0;

  return (
    <div className="relative">
      <div className="flex items-center gap-3 px-3 py-1.5 rounded border border-white/10 bg-zinc-900/60 text-[10px] font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-white/40">notes</span>
          <span className="text-white/80">{stats.total_notes}</span>
        </div>
        <div className="w-px h-3 bg-white/10" />
        <div className="flex items-center gap-1.5">
          <span className="text-white/40">processed</span>
          <span className="text-white/80">{stats.processed}</span>
        </div>
        <div className="w-px h-3 bg-white/10" />
        <div className="flex items-center gap-1.5">
          <span className="text-white/40">backlog</span>
          <span className={hasBacklog ? "text-amber-300" : "text-emerald-400"}>
            {stats.backlog}
          </span>
        </div>
        {stats.current_student && stats.stage !== "waiting_for_note" && stats.stage !== "cycle_complete" && (
          <>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                isEnriching ? "bg-cyan-400 animate-pulse" : hasBacklog ? "bg-amber-400 animate-pulse" : "bg-emerald-400"
              }`} />
              <span className="text-white/60">
                {stats.stage?.replace(/_/g, " ")} &gt; {stats.current_student}
              </span>
              {isEnriching && stats.enrich_progress && (
                <span className="text-white/30">({stats.enrich_progress})</span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
