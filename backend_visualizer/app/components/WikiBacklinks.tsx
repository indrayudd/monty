"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

// Behavioral KG palette (7 types)
const LEGEND_ITEMS = [
  { label: "Emotional", color: "#f97316" },   // orange
  { label: "Social", color: "#3b82f6" },       // blue
  { label: "Cognitive", color: "#a855f7" },    // purple
  { label: "Motor", color: "#22c55e" },        // green
  { label: "Sensory", color: "#eab308" },      // yellow
  { label: "Language", color: "#ec4899" },     // pink
  { label: "Behavioral", color: "#ef4444" },   // red
];

const HEADER_STYLE: React.CSSProperties = {
  fontSize: 10,
  letterSpacing: "1.2px",
  textTransform: "uppercase",
  color: "rgba(255,255,255,0.4)",
};

// Extract outgoing markdown links from page body
function extractOutgoing(body: string): string[] {
  const results: string[] = [];
  // Markdown links: [text](href)
  const mdLink = /\[([^\]]*)\]\(([^)]+)\)/g;
  let m;
  while ((m = mdLink.exec(body)) !== null) {
    const href = m[2];
    // Skip external URLs and anchors
    if (!href.startsWith("http") && !href.startsWith("#") && !href.startsWith("mailto")) {
      results.push(href);
    }
  }
  // Wiki-style [[slug]] links
  const wikiLink = /\[\[([^\]]+)\]\]/g;
  while ((m = wikiLink.exec(body)) !== null) {
    results.push(m[1]);
  }
  return [...new Set(results)];
}

// Lightweight backlinks scan: load every page and text-search for the
// selected path / slug. This is O(N) pages per selection and is intentional
// — the wiki is small, and we want correctness over precision indexing.
export function WikiBacklinks({ path }: { path: string | null }) {
  const [back, setBack] = useState<string[]>([]);
  const [outgoing, setOutgoing] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!path) {
      setBack([]);
      setOutgoing([]);
      return;
    }
    let stop = false;
    (async () => {
      setLoading(true);
      try {
        const [tree, currentPage] = await Promise.all([
          api.wikiTree(),
          api.wikiPage(path).catch(() => null),
        ]);

        // Outgoing: extract from current page body
        if (currentPage && !stop) {
          setOutgoing(extractOutgoing(currentPage.body));
        }

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
    <aside className="w-[320px] shrink-0 border-l border-white/10 bg-zinc-950 overflow-y-auto p-3 text-xs text-white/70 font-mono flex flex-col gap-4">
      {/* GRAPH LINKS header */}
      <div style={HEADER_STYLE}>Graph Links</div>

      {/* Backlinks (incoming) */}
      <section>
        <div className="mb-1 text-white/40 text-[10px]">Incoming</div>
        {loading && <div className="text-white/30">searching…</div>}
        {!loading && back.length === 0 && (
          <div className="text-white/30">(none)</div>
        )}
        {back.map((p) => (
          <div key={p} className="py-1 text-white/80 break-all">
            {p}
          </div>
        ))}
      </section>

      {/* Outgoing links */}
      <section>
        <div className="mb-1 text-white/40 text-[10px]">Outgoing</div>
        {outgoing.length === 0 && (
          <div className="text-white/30">(none)</div>
        )}
        {outgoing.map((href) => (
          <div key={href} className="py-1 text-sky-400/80 break-all">
            {href}
          </div>
        ))}
      </section>

      {/* Legend */}
      <section>
        <div className="mb-2 text-white/40 text-[10px]">Legend</div>
        <div className="flex flex-col gap-1.5">
          {LEGEND_ITEMS.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
              <span className="text-white/60 text-[10px]">{label}</span>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
