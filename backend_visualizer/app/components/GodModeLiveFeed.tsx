"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type FeedLine = {
  ts: string;
  stage: string;
  student: string;
};

function formatTs(d: Date): string {
  return d.toISOString().slice(11, 23); // HH:MM:SS.mmm
}

export function GodModeLiveFeed() {
  const [lines, setLines] = useState<FeedLine[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = (await api.demoOverview()) as {
          runtime?: { current_stage?: string; current_student?: string };
        };
        const stage = r?.runtime?.current_stage || "idle";
        const student = r?.runtime?.current_student || "—";
        const ts = formatTs(new Date());
        setLines((prev) => {
          const next = [...prev, { ts, stage, student }];
          return next.length > 50 ? next.slice(next.length - 50) : next;
        });
      } catch {
        /* keep previous lines */
      }
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="rounded border border-white/10 bg-zinc-950/80 flex flex-col" style={{ minHeight: 180 }}>
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/10">
        <span className="text-[10px] font-mono text-white/50 uppercase tracking-wider">
          Live Event Feed
        </span>
        <span className="text-[9px] font-mono text-white/30">{lines.length}/50</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 max-h-48" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
        {lines.length === 0 && (
          <div className="text-[10px] text-white/30 italic">waiting for agent activity…</div>
        )}
        {lines.map((l, i) => (
          <div key={i} className="text-[11px] text-white/70 leading-relaxed">
            <span className="text-white/30 select-none">{l.ts} </span>
            <span className="text-amber-300/80">{l.stage.replace(/_/g, " ")}</span>
            {l.student !== "—" && (
              <span className="text-white/50"> &gt; {l.student}</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
