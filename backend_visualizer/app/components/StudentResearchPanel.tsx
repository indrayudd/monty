"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Paper = {
  openalex_id?: string;
  title?: string;
  authors?: string | string[];
  publication_year?: number;
  year?: number;
  cited_by_count?: number;
  landing_page_url?: string;
  relevance_summary?: string;
  fetched_for_query?: string;
};

export function StudentResearchPanel({ studentName }: { studentName: string }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = (await api.studentResearch(studentName)) as {
          papers?: Paper[];
        };
        if (!stop) {
          setPapers(r.papers || []);
          setDegraded(false);
        }
      } catch {
        if (!stop) setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => {
      stop = true;
      clearInterval(i);
    };
  }, [studentName]);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-2 bg-zinc-950">
      <div className="text-[11px] text-white/50 font-mono mb-2">
        Research the agent has fetched for {studentName}
        {papers.length > 0 && (
          <span className="ml-2 text-white/40">· {papers.length} paper(s)</span>
        )}
      </div>
      {degraded && (
        <div className="text-[11px] text-amber-300/80 font-mono bg-amber-950/40 border border-amber-500/20 rounded px-2 py-1">
          ⚠ research endpoint unreachable
        </div>
      )}
      {papers.length === 0 && !degraded && (
        <div className="text-white/40 font-mono text-xs py-4">
          No research fetched for {studentName} yet. The curiosity gate fires
          when behavioral nodes accumulate enough support_count + students_count
          to cross threshold 0.70. You can also force it via God Mode →
          Manual research trigger.
        </div>
      )}
      {papers.map((p, i) => {
        const authors = Array.isArray(p.authors)
          ? p.authors.join(", ")
          : p.authors;
        return (
          <article
            key={p.openalex_id || i}
            className="border border-white/10 rounded p-3 bg-zinc-900/60 text-white/80 text-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold text-white flex-1 leading-snug">
                {p.title || "Untitled"}
              </h3>
              <span className="text-[10px] text-white/40 font-mono shrink-0">
                {p.publication_year || p.year || "—"}
                {typeof p.cited_by_count === "number" && (
                  <>
                    {" · "}cited {p.cited_by_count}
                  </>
                )}
              </span>
            </div>
            {authors && (
              <div className="text-xs text-white/60 mt-1 italic">{authors}</div>
            )}
            {(p.relevance_summary || p.fetched_for_query) && (
              <div className="text-xs text-white/70 mt-2">
                {p.relevance_summary || `Query: ${p.fetched_for_query}`}
              </div>
            )}
            {p.landing_page_url && (
              <a
                href={p.landing_page_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-sky-400 underline mt-2 inline-block font-mono"
              >
                open ↗
              </a>
            )}
          </article>
        );
      })}
    </div>
  );
}
