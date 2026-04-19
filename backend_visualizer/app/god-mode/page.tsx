"use client";
import { useEffect, useState } from "react";
import { api, type Persona } from "../lib/api";
import { PersonaCard } from "../components/PersonaCard";
import { StoryPresetRow } from "../components/StoryPresetRow";
import { CuriosityTuning } from "../components/CuriosityTuning";
import { ManualResearchTrigger } from "../components/ManualResearchTrigger";
import { GodModeLiveFeed } from "../components/GodModeLiveFeed";

type Override = {
  slider?: number;
  flavor_override?: string;
  activity_weight?: number;
};

export default function GodModePage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [streaming, setStreaming] = useState<boolean | null>(null);
  const [agentRunning, setAgentRunning] = useState<boolean | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.personas();
        setPersonas(r.personas || []);
        const ov = (r.overrides as Record<string, unknown>) || {};
        setOverrides(ov as Record<string, Override>);
        setStreaming(prev => prev === null ? !ov._paused : prev);
        setAgentRunning(prev => prev === null ? !ov._agent_paused : prev);
      } catch {
        /* keep */
      }
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, []);

  const activeCount = personas.filter((p) => {
    const ov = overrides[p.name];
    return !ov || (ov.activity_weight ?? 1) > 0;
  }).length;

  const handleToggleStream = async () => {
    try {
      if (streaming) {
        await api.pauseStreamer();
        setStreaming(false);
      } else {
        await api.resumeStreamer();
        setStreaming(true);
      }
    } catch {
      /* offline */
    }
  };

  const handleReindex = async () => {
    try {
      const r = await api.wikiReindex();
      alert(`Reindexed: ${JSON.stringify(r)}`);
    } catch (e) {
      alert("Reindex failed: " + String(e));
    }
  };

  const handlePurge = async () => {
    if (
      !confirm(
        "PURGE ALL data? This truncates every table and wipes all wiki content except personas. The streamer + agent loop will rebuild from scratch.",
      )
    )
      return;
    try {
      const r = await api.purge();
      alert(r.message || "Purged.");
      window.location.reload();
    } catch (e) {
      alert("Purge failed: " + String(e));
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex gap-0">
      {/* LEFT COLUMN — 480px, surface-container-low, gold top border */}
      <aside
        className="w-[480px] shrink-0 border-t-2 border-amber-400 bg-zinc-900/60 overflow-y-auto flex flex-col gap-0 p-4"
        style={{ minHeight: "100vh" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-base font-bold text-white">God Mode Control</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] text-white/50 font-mono">
                {activeCount} ACTIVE
              </span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-emerald-500 text-white">
                ⚡ LIVE
              </span>
            </div>
          </div>
        </div>

        {/* Story Presets */}
        <section className="mb-4">
          <h2 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">
            Story Presets
          </h2>
          <StoryPresetRow />
        </section>

        {/* Persona Cards */}
        <section>
          <h2 className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">
            Personas
          </h2>
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
        </section>
      </aside>

      {/* RIGHT COLUMN — fill, vertical stack with 12px gap */}
      <main className="flex-1 min-w-0 p-4 flex flex-col gap-3 overflow-y-auto">
        {/* 1. Live Event Feed */}
        <GodModeLiveFeed />

        {/* 2. Note Generation — cadence + start/stop toggle */}
        <div className="border border-white/10 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider">
              Note Generation
            </div>
            <button
              onClick={handleToggleStream}
              disabled={streaming === null}
              className={`px-4 py-1.5 rounded text-xs font-mono transition-colors ${
                streaming
                  ? "bg-rose-700 hover:bg-rose-600 text-white"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              } disabled:opacity-30`}
            >
              {streaming ? "Stop" : "Start"}
            </button>
          </div>
          <NoteCadenceControl />
        </div>

        {/* 2.5. Agent Loop — pause/resume */}
        <div className="border border-white/10 rounded p-3">
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider">
              Agent Loop
            </div>
            <button
              onClick={async () => {
                try {
                  if (agentRunning) {
                    await api.pauseAgent();
                    setAgentRunning(false);
                  } else {
                    await api.resumeAgent();
                    setAgentRunning(true);
                  }
                } catch {}
              }}
              disabled={agentRunning === null}
              className={`px-4 py-1.5 rounded text-xs font-mono transition-colors ${
                agentRunning
                  ? "bg-rose-700 hover:bg-rose-600 text-white"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              } disabled:opacity-30`}
            >
              {agentRunning ? "Pause" : "Resume"}
            </button>
          </div>
          <div className="text-[9px] text-white/40 font-mono mt-1">
            {agentRunning ? "Agent is processing notes and researching" : "Agent is on standby"}
          </div>
        </div>

        {/* 3. Curiosity Presets */}
        <CuriosityTuning />

        {/* 4. Manual Research Trigger */}
        <ManualResearchTrigger />

        {/* 5. Maintenance */}
        <div className="flex gap-2">
          <button
            onClick={handleReindex}
            className="flex-1 px-3 py-2 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white/70 font-mono transition-colors"
          >
            Reindex wiki
          </button>
          <button
            onClick={handlePurge}
            className="flex-1 px-3 py-2 rounded bg-rose-950 hover:bg-rose-900 border border-rose-700/50 text-xs text-rose-300 font-mono transition-colors"
          >
            Purge everything
          </button>
        </div>
      </main>
    </div>
  );
}

// Logarithmic cadence: slider 0–100 maps to 0s–86400s (1/day)
const CADENCE_PRESETS = [
  { label: "Auto", value: 0 },
  { label: "1/s", value: 1 },
  { label: "1/5s", value: 5 },
  { label: "1/30s", value: 30 },
  { label: "1/min", value: 60 },
  { label: "1/5m", value: 300 },
  { label: "1/hr", value: 3600 },
  { label: "1/day", value: 86400 },
];

function formatCadence(v: number): string {
  if (v <= 0) return "auto (2–8s)";
  if (v < 60) return `1 every ${v.toFixed(0)}s`;
  if (v < 3600) return `1 every ${(v / 60).toFixed(0)}m`;
  if (v < 86400) return `1 every ${(v / 3600).toFixed(1)}h`;
  return "1/day";
}

function NoteCadenceControl() {
  const [cadence, setCadence] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.getNoteCadence().then((r) => {
      setCadence(r.note_cadence);
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const update = (v: number) => {
    setCadence(v);
    api.setNoteCadence(v).catch(() => {});
  };

  return (
    <div>
      <div className="flex flex-wrap gap-1 mb-2">
        {CADENCE_PRESETS.map((p) => (
          <button
            key={p.value}
            onClick={() => update(p.value)}
            disabled={!loaded}
            className={`text-[9px] font-mono px-2 py-1 rounded transition-colors ${
              cadence === p.value
                ? "bg-white/15 text-white border border-white/20"
                : "bg-white/5 text-white/40 hover:text-white/70 border border-transparent"
            } disabled:opacity-30`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="text-[9px] text-white/40 font-mono">
        current: {formatCadence(cadence)} · max 2 notes/sec
      </div>
    </div>
  );
}
