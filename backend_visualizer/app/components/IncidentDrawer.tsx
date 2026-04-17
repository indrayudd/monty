"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type StudentIncident, type WikiPage } from "../lib/api";

const TYPE_COLORS: Record<string, string> = {
  setting: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  antecedent: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  behavior: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  function: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  brain: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  response: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
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
      <aside className="absolute top-0 right-0 h-full w-[280px] max-w-[95vw] bg-zinc-950 border-l border-white/20 overflow-y-auto p-4 text-white/90 shadow-2xl">
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
