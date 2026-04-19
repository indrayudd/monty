"use client";
import { useState } from "react";
import { api } from "../lib/api";

const PRESETS: Record<string, Record<string, number>> = {
  less: {
    novelty: 0.10,
    recurrence_gap: 0.10,
    cross_student: 0.10,
    surprise: 0.08,
    severity_weight: 0.08,
    recency: 0.05,
  },
  standard: {
    novelty: 0.20,
    recurrence_gap: 0.20,
    cross_student: 0.20,
    surprise: 0.15,
    severity_weight: 0.15,
    recency: 0.10,
  },
  more: {
    novelty: 0.30,
    recurrence_gap: 0.30,
    cross_student: 0.30,
    surprise: 0.22,
    severity_weight: 0.22,
    recency: 0.15,
  },
};

export function CuriosityTuning() {
  const [active, setActive] = useState<string>("standard");

  const apply = (preset: string) => {
    setActive(preset);
    api.curiosityWeights(PRESETS[preset]).catch(() => {});
  };

  return (
    <div className="mt-4 border border-white/10 rounded px-3 py-2">
      <div className="text-[10px] text-white/50 font-mono mb-2 uppercase tracking-wider">
        Curiosity
      </div>
      <div className="flex gap-1">
        {(["less", "standard", "more"] as const).map((preset) => (
          <button
            key={preset}
            onClick={() => apply(preset)}
            className={`flex-1 text-[10px] font-mono py-1.5 rounded transition-colors ${
              active === preset
                ? preset === "more"
                  ? "bg-amber-600/30 text-amber-300 border border-amber-500/30"
                  : preset === "less"
                    ? "bg-blue-600/30 text-blue-300 border border-blue-500/30"
                    : "bg-white/15 text-white border border-white/20"
                : "bg-white/5 text-white/40 hover:text-white/70 hover:bg-white/10 border border-transparent"
            }`}
          >
            {preset === "less" ? "Less" : preset === "standard" ? "Standard" : "More"}
          </button>
        ))}
      </div>
    </div>
  );
}
