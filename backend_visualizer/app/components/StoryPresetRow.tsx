"use client";
import { useState } from "react";
import { api } from "../lib/api";

const PRESETS: Record<
  string,
  Record<string, { slider: number; activity_weight: number }>
> = {
  "Calm Morning": {
    "Arjun Nair": { slider: -0.4, activity_weight: 1 },
    "Diya Malhotra": { slider: -0.5, activity_weight: 1 },
    "Kiaan Gupta": { slider: -0.7, activity_weight: 1 },
    "Mira Shah": { slider: -0.3, activity_weight: 1 },
    "Saanvi Verma": { slider: -0.5, activity_weight: 1 },
  },
  "Escalating Mira": {
    "Arjun Nair": { slider: 0.0, activity_weight: 0.8 },
    "Diya Malhotra": { slider: 0.0, activity_weight: 0.8 },
    "Kiaan Gupta": { slider: -0.3, activity_weight: 0.8 },
    "Mira Shah": { slider: 0.7, activity_weight: 2.0 },
    "Saanvi Verma": { slider: 0.0, activity_weight: 0.8 },
  },
  "Group Conflict": {
    "Arjun Nair": { slider: 0.5, activity_weight: 1.5 },
    "Diya Malhotra": { slider: 0.6, activity_weight: 1.5 },
    "Kiaan Gupta": { slider: 0.3, activity_weight: 1 },
    "Mira Shah": { slider: 0.6, activity_weight: 1.5 },
    "Saanvi Verma": { slider: 0.4, activity_weight: 1 },
  },
  "Emergency Cascade": {
    "Arjun Nair": { slider: 0.8, activity_weight: 1.5 },
    "Diya Malhotra": { slider: 0.8, activity_weight: 1.5 },
    "Kiaan Gupta": { slider: 0.7, activity_weight: 1 },
    "Mira Shah": { slider: 0.95, activity_weight: 2.5 },
    "Saanvi Verma": { slider: 0.7, activity_weight: 1 },
  },
  "Reset to Baseline": {
    "Arjun Nair": { slider: 0, activity_weight: 1 },
    "Diya Malhotra": { slider: 0, activity_weight: 1 },
    "Kiaan Gupta": { slider: 0, activity_weight: 1 },
    "Mira Shah": { slider: 0, activity_weight: 1 },
    "Saanvi Verma": { slider: 0, activity_weight: 1 },
  },
};

export function StoryPresetRow() {
  const [active, setActive] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  const apply = async (name: string) => {
    setApplying(true);
    setActive(name);
    const preset = PRESETS[name];
    await Promise.all(
      Object.entries(preset).map(([n, v]) =>
        api.updatePersona(n, v).catch(() => {}),
      ),
    );
    setApplying(false);
    // Keep the active highlight until another preset is clicked.
  };

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {Object.keys(PRESETS).map((p) => (
        <button
          key={p}
          onClick={() => apply(p)}
          disabled={applying}
          className={`px-3 py-2 rounded border text-xs font-mono transition-colors ${
            active === p
              ? "bg-amber-400/15 border-amber-400/40 text-amber-300"
              : "bg-white/5 hover:bg-white/10 border-white/10 text-white"
          } ${applying ? "opacity-50" : ""}`}
        >
          {p}
          {active === p && !applying && (
            <span className="ml-1.5 text-[9px] text-amber-400/70">✓</span>
          )}
        </button>
      ))}
    </div>
  );
}
