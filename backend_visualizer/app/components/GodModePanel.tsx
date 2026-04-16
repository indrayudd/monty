"use client";
import { useEffect, useState } from "react";
import { api, type Persona } from "../lib/api";
import { PersonaCard } from "./PersonaCard";
import { StoryPresetRow } from "./StoryPresetRow";
import { CuriosityTuning } from "./CuriosityTuning";
import { ManualResearchTrigger } from "./ManualResearchTrigger";

type Override = {
  slider?: number;
  flavor_override?: string;
  activity_weight?: number;
};

export function GodModePanel() {
  const [open, setOpen] = useState(false);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});

  useEffect(() => {
    if (!open) return;
    const tick = async () => {
      try {
        const r = await api.personas();
        setPersonas(r.personas || []);
        setOverrides((r.overrides as Record<string, Override>) || {});
      } catch {
        /* keep */
      }
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-30 px-4 py-3 rounded-full bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold shadow-lg"
      >
        ⚡ God Mode
      </button>
      {open && (
        <div className="fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/30"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute top-0 right-0 h-full w-[420px] bg-zinc-950/95 backdrop-blur border-l border-white/20 overflow-y-auto p-4 text-white">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-sm font-mono">⚡ God Mode</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-white/50 text-xs font-mono hover:text-white"
              >
                esc
              </button>
            </div>
            <StoryPresetRow />
            <div className="space-y-3">
              {personas.length === 0 && (
                <div className="text-xs text-white/40 font-mono border border-dashed border-white/10 rounded p-3">
                  No personas loaded. The persona engine may still be
                  initialising.
                </div>
              )}
              {personas.map((p) => (
                <PersonaCard
                  key={p.name}
                  persona={p}
                  override={overrides[p.name] || {}}
                  otherPersonas={personas
                    .filter((x) => x.name !== p.name)
                    .map((x) => x.name)}
                />
              ))}
            </div>
            <CuriosityTuning />
            <ManualResearchTrigger />
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => {
                  api.demoStart().catch(() => {});
                }}
                className="flex-1 px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-mono"
              >
                Start
              </button>
              <button
                onClick={() => {
                  api.demoReset().catch(() => {});
                }}
                className="flex-1 px-3 py-2 rounded bg-amber-600 hover:bg-amber-500 text-xs text-white font-mono"
              >
                Reset
              </button>
              <button
                onClick={() => {
                  api.demoStop().catch(() => {});
                }}
                className="flex-1 px-3 py-2 rounded bg-rose-700 hover:bg-rose-600 text-xs text-white font-mono"
              >
                Stop
              </button>
            </div>
            <button
              onClick={async () => { const r = await api.wikiReindex(); alert(`Reindexed: ${JSON.stringify(r)}`); }}
              className="mt-2 w-full px-3 py-2 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white/70"
            >
              Reindex wiki (full rebuild)
            </button>
          </aside>
        </div>
      )}
    </>
  );
}
