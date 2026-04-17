"use client";
import { useEffect, useState } from "react";
import { api, type Persona } from "../lib/api";

type Override = {
  slider?: number;
  flavor_override?: string;
  activity_weight?: number;
  inject_next?: string;
  interact_with?: string;
};

export function PersonaCard({
  persona,
  override,
  otherPersonas,
}: {
  persona: Persona;
  override: Override;
  otherPersonas: string[];
}) {
  const [slider, setSlider] = useState<number>(override?.slider ?? 0);
  const [flavor, setFlavor] = useState<string>(
    override?.flavor_override ?? persona.dysfunction_flavor,
  );
  const [activity, setActivity] = useState<number>(
    override?.activity_weight ?? 1,
  );
  const [lastInject, setLastInject] = useState<string | null>(null);
  const [lastInteract, setLastInteract] = useState<string | null>(null);

  // Sync local state when the parent passes updated overrides from the API poll.
  useEffect(() => {
    if (override?.slider !== undefined && override.slider !== slider) {
      setSlider(override.slider);
    }
    if (override?.flavor_override && override.flavor_override !== flavor) {
      setFlavor(override.flavor_override);
    }
    if (override?.activity_weight !== undefined && override.activity_weight !== activity) {
      setActivity(override.activity_weight);
    }
    // Show pending inject/interact from the API (before the streamer consumes them).
    if (override?.inject_next && override.inject_next !== lastInject) {
      setLastInject(override.inject_next);
    } else if (!override?.inject_next && lastInject) {
      // Streamer consumed the inject — clear after a brief display.
      const t = setTimeout(() => setLastInject(null), 2000);
      return () => clearTimeout(t);
    }
    if (override?.interact_with) {
      setLastInteract(override.interact_with);
    } else if (!override?.interact_with && lastInteract) {
      const t = setTimeout(() => setLastInteract(null), 2000);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [override]);

  const flavors = [
    "impulsive",
    "clingy-then-shutdown",
    "scattered",
    "explosive-then-shutdown",
    "shutdown",
  ];

  const update = async (
    patch: {
      slider?: number;
      flavor_override?: string;
      activity_weight?: number;
    },
  ) => {
    try {
      await api.updatePersona(persona.name, patch);
    } catch {
      /* stub / offline */
    }
  };

  const injectColors: Record<string, string> = {
    neutral: "bg-emerald-800/50 border-emerald-600/50",
    problematic: "bg-amber-800/50 border-amber-600/50",
    emergency: "bg-rose-800/50 border-rose-600/50",
    surprise: "bg-violet-800/50 border-violet-600/50",
  };

  return (
    <div className="border border-white/10 rounded-lg p-3 bg-zinc-900/80">
      <div className="flex items-center justify-between mb-1">
        <div>
          <span className="font-semibold text-white">{persona.name}</span>
          <span className="ml-2 text-[11px] text-white/50 font-mono">
            {persona.age_band}
          </span>
        </div>
        <span className="text-[10px] text-white/40 font-mono">
          {persona.dysfunction_flavor}
        </span>
      </div>

      {/* Status badges */}
      <div className="flex gap-1 mb-2 min-h-[18px]">
        {lastInject && (
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${injectColors[lastInject] || "bg-white/10"} text-white/80`}>
            next: {lastInject}
          </span>
        )}
        {lastInteract && (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-mono bg-sky-800/50 border border-sky-600/50 text-white/80">
            interacting with {lastInteract}
          </span>
        )}
      </div>

      <label className="block text-[10px] text-white/60 mb-1 font-mono">
        Functional ↔ Dysfunctional ({slider.toFixed(1)})
      </label>
      <input
        type="range"
        min={-1}
        max={1}
        step={0.1}
        value={slider}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          setSlider(v);
          update({ slider: v });
        }}
        className="w-full accent-rose-400"
      />
      <div className="flex gap-2 mt-2">
        <select
          value={flavor}
          onChange={(e) => {
            setFlavor(e.target.value);
            update({ flavor_override: e.target.value });
          }}
          className="bg-zinc-800 text-xs px-2 py-1 rounded border border-white/10 flex-1 text-white font-mono"
        >
          {flavors.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={0}
          max={3}
          step={0.1}
          value={activity}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            setActivity(v);
            update({ activity_weight: v });
          }}
          className="bg-zinc-800 text-xs px-2 py-1 rounded border border-white/10 w-16 text-white font-mono"
          title="activity weight (0 = paused, 1 = normal, 2 = double)"
        />
      </div>
      <div className="flex gap-1 mt-2">
        {(["neutral", "problematic", "emergency", "surprise"] as const).map(
          (f) => (
            <button
              key={f}
              onClick={async () => {
                try {
                  await api.injectPersona(persona.name, f);
                  setLastInject(f);
                } catch {
                  /* offline */
                }
              }}
              className={`flex-1 text-[10px] py-1.5 rounded border capitalize font-mono transition-colors ${
                lastInject === f
                  ? injectColors[f]
                  : "bg-white/5 hover:bg-white/10 border-white/10"
              }`}
            >
              {f}
            </button>
          ),
        )}
      </div>
      <div className="flex gap-1 mt-2 items-center">
        <span className="text-[10px] text-white/50 font-mono">interact:</span>
        <select
          value={lastInteract || ""}
          onChange={async (e) => {
            if (e.target.value) {
              try {
                await api.interactPersonas(persona.name, e.target.value);
                setLastInteract(e.target.value);
              } catch {
                /* offline */
              }
            }
          }}
          className="bg-zinc-800 text-[10px] px-2 py-1 rounded border border-white/10 flex-1 text-white font-mono"
        >
          <option value="">— pick peer —</option>
          {otherPersonas.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
