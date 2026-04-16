"use client";
import { useState } from "react";
import { api } from "../lib/api";

export function ManualResearchTrigger() {
  const [slug, setSlug] = useState("");
  const [last, setLast] = useState<{
    fire?: boolean;
    score?: number;
    reason?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fire = async () => {
    if (!slug.trim()) return;
    setError(null);
    try {
      const r = await api.curiosityInvestigate(slug.trim());
      setLast(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed");
    }
  };

  return (
    <div className="mt-4 border border-white/10 rounded p-3">
      <div className="text-xs text-white/70 font-mono mb-2">
        Manual research trigger
      </div>
      <div className="flex gap-2">
        <input
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          placeholder="behavioral node slug"
          className="bg-zinc-800 px-2 py-1 rounded text-xs border border-white/10 flex-1 text-white font-mono"
          onKeyDown={(e) => {
            if (e.key === "Enter") fire();
          }}
        />
        <button
          onClick={fire}
          className="px-3 py-1 text-xs rounded bg-rose-600 hover:bg-rose-500 text-white font-mono"
        >
          Investigate
        </button>
      </div>
      {last && (
        <div className="mt-2 text-[10px] font-mono text-white/60">
          fire={String(last.fire)} score=
          {last.score != null ? last.score.toFixed(3) : "—"} reason=
          {last.reason || "—"}
        </div>
      )}
      {error && (
        <div className="mt-2 text-[10px] font-mono text-amber-300/80">
          ⚠ {error}
        </div>
      )}
    </div>
  );
}
