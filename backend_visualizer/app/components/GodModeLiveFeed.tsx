"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type FeedLine = {
  ts: string;
  kind: "stage" | "note";
  text: string;
  detail?: string;
};

function formatTs(d: Date): string {
  return d.toISOString().slice(11, 23);
}

export function GodModeLiveFeed() {
  const [lines, setLines] = useState<FeedLine[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastNoteIdRef = useRef<number>(0);

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, notesRes] = await Promise.all([
          api.demoOverview() as Promise<{
            runtime?: { current_stage?: string; current_student?: string };
          }>,
          api.recentNotes(3),
        ]);

        const ts = formatTs(new Date());
        const newLines: FeedLine[] = [];

        // Stage line
        const stage = overview?.runtime?.current_stage || "idle";
        const student = overview?.runtime?.current_student || "";
        newLines.push({
          ts,
          kind: "stage",
          text: stage.replace(/_/g, " "),
          detail: student || undefined,
        });

        // Note emission lines (only show truly new ones)
        const notes = notesRes?.notes || [];
        for (const n of notes) {
          if (n.id > lastNoteIdRef.current) {
            lastNoteIdRef.current = Math.max(lastNoteIdRef.current, n.id);
            const preview = (n.body || "").replace(/^Name:.*\n+/, "").slice(0, 80).replace(/\n/g, " ");
            newLines.push({
              ts,
              kind: "note",
              text: `note #${n.id} → ${n.name}`,
              detail: preview + (preview.length >= 80 ? "…" : ""),
            });
          }
        }

        setLines((prev) => {
          const next = [...prev, ...newLines];
          return next.length > 80 ? next.slice(next.length - 80) : next;
        });
      } catch {
        /* keep */
      }
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <div className="rounded border border-white/10 bg-zinc-950/80 flex flex-col" style={{ minHeight: 220 }}>
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/10">
        <span className="text-[10px] font-mono text-white/50 uppercase tracking-wider">
          Live Event Feed
        </span>
        <span className="text-[9px] font-mono text-white/30">
          {lines.length}/80
        </span>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2 max-h-64"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        {lines.length === 0 && (
          <div className="text-[10px] text-white/30 italic">
            waiting for agent activity…
          </div>
        )}
        {lines.map((l, i) => (
          <div key={i} className="text-[11px] leading-relaxed">
            <span className="text-white/25 select-none">{l.ts} </span>
            {l.kind === "stage" ? (
              <>
                <span className="text-amber-300/70">{l.text}</span>
                {l.detail && (
                  <span className="text-white/40"> &gt; {l.detail}</span>
                )}
              </>
            ) : (
              <>
                <span className="text-emerald-400/80">{l.text}</span>
                {l.detail && (
                  <div className="ml-[96px] text-[10px] text-white/35 truncate">
                    {l.detail}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
