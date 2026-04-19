"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Note = { id: number; name: string; body: string; inserted_at: string };

export function NotesPipelineWidget() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [stats, setStats] = useState<{ total_notes: number; processed: number; backlog: number } | null>(null);
  const [cadence, setCadence] = useState<number>(0);
  const [paused, setPaused] = useState<boolean | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const [notesRes, statsRes, cadenceRes, personasRes] = await Promise.all([
          api.recentNotes(5),
          api.ingestionStats(),
          api.getNoteCadence(),
          api.personas(),
        ]);
        setNotes(notesRes.notes || []);
        setStats(statsRes);
        setCadence(cadenceRes.note_cadence);
        const ov = (personasRes.overrides as Record<string, unknown>) || {};
        setPaused(!!ov._paused);
      } catch {}
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => clearInterval(i);
  }, []);

  const cadenceLabel = cadence <= 0 ? "auto (2-8s)" : cadence < 60 ? `${cadence}s` : cadence < 3600 ? `${Math.round(cadence / 60)}m` : `${(cadence / 3600).toFixed(1)}h`;

  return (
    <div className="grid grid-cols-2 gap-3">
      {/* Streamer Status */}
      <div className="border border-white/10 rounded p-3 bg-zinc-950">
        <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
          Note Streamer
        </div>
        <div className="flex items-center gap-2 mb-2">
          <span className={`w-2 h-2 rounded-full ${paused === false ? "bg-emerald-400 animate-pulse" : paused === true ? "bg-rose-400" : "bg-zinc-600"}`} />
          <span className="text-xs font-mono text-white/80">{paused === false ? "Running" : paused === true ? "Paused" : "Unknown"}</span>
        </div>
        <div className="space-y-1 text-[10px] font-mono text-white/50">
          <div className="flex justify-between">
            <span>cadence</span>
            <span className="text-white/70">{cadenceLabel}</span>
          </div>
          <div className="flex justify-between">
            <span>total emitted</span>
            <span className="text-white/70">{stats?.total_notes ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span>processed</span>
            <span className="text-white/70">{stats?.processed ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span>backlog</span>
            <span className={`${(stats?.backlog ?? 0) > 5 ? "text-amber-300" : "text-emerald-400"}`}>{stats?.backlog ?? "—"}</span>
          </div>
        </div>
      </div>

      {/* Recent Notes */}
      <div className="border border-white/10 rounded p-3 bg-zinc-950">
        <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2">
          Recent Notes (DB)
        </div>
        {notes.length === 0 && (
          <div className="text-[10px] font-mono text-white/25 italic">no notes yet</div>
        )}
        <div className="space-y-1.5 max-h-32 overflow-y-auto">
          {notes.map((n) => {
            const ago = (() => {
              // DB timestamps are UTC but lack timezone suffix
              const ts = n.inserted_at.endsWith("Z") ? n.inserted_at : n.inserted_at + "Z";
              const s = Math.max(0, (Date.now() - new Date(ts).getTime()) / 1000);
              return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`;
            })();
            const preview = (n.body || "").replace(/^Name:.*\n+/, "").slice(0, 50).replace(/\n/g, " ");
            return (
              <div key={n.id} className="flex items-start gap-2 text-[10px] font-mono">
                <span className="text-white/25 shrink-0 w-8 text-right">{ago}</span>
                <span className="text-emerald-400/80 shrink-0">#{n.id}</span>
                <span className="text-white/50 truncate">{n.name}</span>
                <span className="text-white/25 truncate flex-1">{preview}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
