"use client";
import { useState } from "react";
import { api, type Persona } from "../lib/api";

type Override = {
  slider?: number;
  flavor_override?: string;
  activity_weight?: number;
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
      /* stub / offline; silently no-op */
    }
  };

  return (
    <div className="border border-white/10 rounded-lg p-3 bg-zinc-900/80">
      <div className="flex items-center justify-between mb-2">
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
          title="activity weight"
        />
      </div>
      <div className="flex gap-1 mt-2">
        {(["neutral", "problematic", "emergency", "surprise"] as const).map(
          (f) => (
            <button
              key={f}
              onClick={() => {
                api.injectPersona(persona.name, f).catch(() => {});
              }}
              className="flex-1 text-[10px] py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 capitalize font-mono"
            >
              {f}
            </button>
          ),
        )}
      </div>
      <div className="flex gap-1 mt-2 items-center">
        <span className="text-[10px] text-white/50 font-mono">interact:</span>
        <select
          onChange={(e) => {
            if (e.target.value) {
              api
                .interactPersonas(persona.name, e.target.value)
                .catch(() => {});
            }
          }}
          className="bg-zinc-800 text-[10px] px-2 py-1 rounded border border-white/10 flex-1 text-white font-mono"
          defaultValue=""
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
