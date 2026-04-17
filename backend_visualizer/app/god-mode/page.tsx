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

type DemoStatus = "idle" | "running" | "stopped";

export default function GodModePage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [demoStatus, setDemoStatus] = useState<DemoStatus>("idle");

  useEffect(() => {
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
  }, []);

  const activeCount = personas.filter((p) => {
    const ov = overrides[p.name];
    return !ov || (ov.activity_weight ?? 1) > 0;
  }).length;

  const handleStart = async () => {
    try {
      await api.resumeStreamer();
      setDemoStatus("running");
    } catch {
      /* offline */
    }
  };

  const handleStop = async () => {
    try {
      await api.pauseStreamer();
      setDemoStatus("stopped");
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

  const statusColors: Record<DemoStatus, string> = {
    idle: "bg-white/10 text-white/50",
    running: "bg-emerald-500/20 text-emerald-300",
    stopped: "bg-rose-500/20 text-rose-300",
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

        {/* 2. Curiosity Weights — rendered expanded */}
        <div className="border border-white/10 rounded">
          <div className="px-3 py-2 text-xs text-white/70 font-mono border-b border-white/10">
            ▼ Curiosity tuning
          </div>
          <CuriosityTuningExpanded />
        </div>

        {/* 3. Manual Research Trigger */}
        <ManualResearchTrigger />

        {/* 3.5. Note Cadence Control */}
        <NoteCadenceControl />

        {/* 4. Demo Lifecycle */}
        <div className="border border-white/10 rounded p-3">
          <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-3">
            Demo Lifecycle
          </div>

          {/* Start / Reset / Stop + status badge */}
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={handleStart}
              className="flex-1 px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-mono transition-colors"
            >
              Start
            </button>
            <button
              onClick={handleStop}
              className="flex-1 px-3 py-2 rounded bg-rose-700 hover:bg-rose-600 text-xs text-white font-mono transition-colors"
            >
              Stop
            </button>
            <span
              className={`px-2 py-1 rounded text-[10px] font-mono capitalize ${statusColors[demoStatus]}`}
            >
              {demoStatus}
            </span>
          </div>

          {/* Reindex + Purge */}
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
        </div>
      </main>
    </div>
  );
}

// Inline expanded version of CuriosityTuning (avoids modifying the original component)
const CURIOSITY_KEYS = [
  "novelty",
  "recurrence_gap",
  "cross_student",
  "surprise",
  "severity_weight",
  "recency",
];
const CURIOSITY_DEFAULTS: Record<string, number> = {
  novelty: 0.2,
  recurrence_gap: 0.2,
  cross_student: 0.2,
  surprise: 0.15,
  severity_weight: 0.15,
  recency: 0.1,
};

function CuriosityTuningExpanded() {
  const [w, setW] = useState<Record<string, number>>({ ...CURIOSITY_DEFAULTS });

  const update = (k: string, v: number) => {
    const next = { ...w, [k]: v };
    setW(next);
    api.curiosityWeights({ [k]: v }).catch(() => {});
  };

  return (
    <div className="p-3 space-y-2">
      {CURIOSITY_KEYS.map((k) => (
        <div key={k}>
          <label className="block text-[10px] text-white/60 font-mono">
            {k}: {w[k].toFixed(2)}
          </label>
          <input
            type="range"
            min={0}
            max={0.5}
            step={0.01}
            value={w[k]}
            onChange={(e) => update(k, parseFloat(e.target.value))}
            className="w-full"
          />
        </div>
      ))}
    </div>
  );
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

  const label = cadence <= 0
    ? "random 2–8s (default)"
    : `${cadence.toFixed(1)}s (±20% jitter)`;

  return (
    <div className="border border-white/10 rounded p-3">
      <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider mb-2">
        Note Generation Cadence
      </div>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={10}
          step={0.5}
          value={cadence}
          onChange={(e) => update(parseFloat(e.target.value))}
          className="flex-1"
          disabled={!loaded}
        />
        <span className="text-xs font-mono text-white/70 w-44 text-right">{label}</span>
      </div>
      <div className="text-[9px] text-white/40 font-mono mt-1">
        0 = random 2–8s · higher = slower · streamer reads this on each tick
      </div>
    </div>
  );
}
