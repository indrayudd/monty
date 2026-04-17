"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type StudentIncident, type WikiPage } from "../lib/api";

// From DESIGN.md § 2 — 10% opacity bg + full-opacity text per the "Slim Pills" rule
const TYPE_COLORS: Record<string, string> = {
  setting: "border-[#00D8FF]/30 text-[#00D8FF]",       // Cyan
  antecedent: "border-[#BC8CFF]/30 text-[#BC8CFF]",    // Purple
  behavior: "border-[#FFA657]/30 text-[#FFA657]",      // Orange
  function: "border-[#FF7EB6]/30 text-[#FF7EB6]",      // Magenta
  brain: "border-[#79C0FF]/30 text-[#79C0FF]",         // Indigo
  response: "border-[#3FB950]/30 text-[#3FB950]",      // Teal
};

export function IncidentDrawer({
  incident,
  onClose,
  onSelectBehavioralNode,
}: {
  incident: StudentIncident | null;
  onClose: () => void;
  onSelectBehavioralNode: (slug: string) => void;
}) {
  const [page, setPage] = useState<WikiPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!incident) {
      setPage(null);
      setError(null);
      return;
    }
    setPage(null);
    setError(null);
    api
      .wikiPage(incident.file_path)
      .then(setPage)
      .catch(() => setError("Could not load incident page."));
  }, [incident?.id, incident?.file_path]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!incident) return null;

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute top-0 right-0 h-full w-[480px] max-w-[95vw] bg-zinc-950 border-l border-white/20 overflow-y-auto p-4 text-white/90 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-mono text-xs text-white/60 truncate">
            {incident.file_path}
          </h2>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white font-mono text-xs"
          >
            esc
          </button>
        </div>
        {error && (
          <div className="text-amber-300/80 font-mono text-xs mb-4">
            {error}
          </div>
        )}
        {page ? (
          <>
            <div className="mb-4 text-xs text-white/60 font-mono border border-white/10 rounded p-3 bg-black/40 space-y-0.5">
              {Object.entries(page.frontmatter).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-white/40 w-32 shrink-0">{k}:</span>
                  <span className="text-white/80 break-all">
                    {Array.isArray(v) ? v.join(", ") : String(v)}
                  </span>
                </div>
              ))}
            </div>
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {page.body}
              </ReactMarkdown>
            </div>
            <div className="mt-6">
              <h3 className="font-mono text-xs text-white/60 mb-2">
                Linked behavioral nodes
              </h3>
              <div className="flex flex-wrap gap-2">
                {(
                  page.frontmatter.behavioral_refs as string[] | undefined
                )?.map((ref) => {
                  const slug = ref.split("/").slice(-1)[0];
                  const parts = ref.split("/");
                  const typeKey = parts.length >= 2 ? parts[parts.length - 2] : "";
                  const colors = TYPE_COLORS[typeKey.toLowerCase()] || "bg-white/5 text-white/80 border-white/10";
                  return (
                    <button
                      key={ref}
                      onClick={() => {
                        onSelectBehavioralNode(slug);
                        onClose();
                      }}
                      className={`text-xs px-2 py-1 rounded border font-mono hover:brightness-125 ${colors}`}
                    >
                      {slug}
                    </button>
                  );
                })}
                {!page.frontmatter.behavioral_refs && (
                  <span className="text-white/30 text-xs font-mono">
                    (none)
                  </span>
                )}
              </div>
            </div>
          </>
        ) : !error ? (
          <div className="text-white/40 font-mono text-xs">loading…</div>
        ) : null}
      </aside>
    </div>
  );
}
