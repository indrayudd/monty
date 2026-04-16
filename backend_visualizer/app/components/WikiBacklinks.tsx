"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

// Lightweight backlinks scan: load every page and text-search for the
// selected path / slug. This is O(N) pages per selection and is intentional
// — the wiki is small, and we want correctness over precision indexing.
export function WikiBacklinks({ path }: { path: string | null }) {
  const [back, setBack] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!path) {
      setBack([]);
      return;
    }
    let stop = false;
    (async () => {
      setLoading(true);
      try {
        const tree = await api.wikiTree();
        const hits: string[] = [];
        // The search needle is both the full path and its basename (minus .md)
        // so that wiki-style [[peer-takes-material]] still matches.
        const basename = path.split("/").pop()?.replace(/\.md$/, "") || "";
        for (const f of tree.files) {
          if (stop) break;
          if (f.path === path) continue;
          try {
            const page = await api.wikiPage(f.path);
            if (
              page.raw.includes(path) ||
              (basename && page.raw.includes(basename))
            ) {
              hits.push(f.path);
            }
          } catch {
            /* skip */
          }
        }
        if (!stop) setBack(hits);
      } finally {
        if (!stop) setLoading(false);
      }
    })();
    return () => {
      stop = true;
    };
  }, [path]);

  return (
    <aside className="w-[280px] shrink-0 border-l border-white/10 bg-zinc-950 overflow-y-auto p-3 text-xs text-white/70 font-mono">
      <div className="mb-2 text-white/50">Linked from</div>
      {loading && <div className="text-white/30">searching…</div>}
      {!loading && back.length === 0 && (
        <div className="text-white/30">(none)</div>
      )}
      {back.map((p) => (
        <div key={p} className="py-1 text-white/80 break-all">
          {p}
        </div>
      ))}
    </aside>
  );
}
