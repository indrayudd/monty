"use client";
import { useState } from "react";
import { api } from "../lib/api";

const KEYS = [
  "novelty",
  "recurrence_gap",
  "cross_student",
  "surprise",
  "severity_weight",
  "recency",
];
const DEFAULTS: Record<string, number> = {
  novelty: 0.2,
  recurrence_gap: 0.2,
  cross_student: 0.2,
  surprise: 0.15,
  severity_weight: 0.15,
  recency: 0.1,
};

export function CuriosityTuning() {
  const [open, setOpen] = useState(false);
  const [w, setW] = useState<Record<string, number>>({ ...DEFAULTS });

  const update = (k: string, v: number) => {
    const next = { ...w, [k]: v };
    setW(next);
    api.curiosityWeights({ [k]: v }).catch(() => {});
  };

  return (
    <div className="mt-4 border border-white/10 rounded">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left px-3 py-2 text-xs text-white/70 font-mono"
      >
        {open ? "▼" : "▶"} Curiosity tuning
      </button>
      {open && (
        <div className="p-3 space-y-2">
          {KEYS.map((k) => (
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
      )}
    </div>
  );
}
