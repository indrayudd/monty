"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type WikiPage } from "../lib/api";

export function WikiPageRenderer({
  path,
  onNavigate,
}: {
  path: string | null;
  onNavigate: (p: string) => void;
}) {
  const [page, setPage] = useState<WikiPage | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setPage(null);
      setError(null);
      return;
    }
    setPage(null);
    setError(null);
    api
      .wikiPage(path)
      .then(setPage)
      .catch(() => setError("page not found"));
  }, [path]);

  if (!path)
    return (
      <div className="flex-1 p-6 text-white/40 font-mono text-sm">
        Select a file from the tree.
      </div>
    );
  if (error)
    return (
      <div className="flex-1 p-6 text-amber-300/80 font-mono text-sm">
        ⚠ {error}
      </div>
    );
  if (!page)
    return (
      <div className="flex-1 p-6 text-white/40 font-mono text-sm">
        loading…
      </div>
    );

  const components = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    a: (props: any) => {
      const href: string = props.href || "";
      if (href.endsWith(".md")) {
        return (
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onNavigate(href.replace(/^\.\.?\//, ""));
            }}
            className="text-sky-400 underline"
          >
            {props.children}
          </a>
        );
      }
      return (
        <a
          {...props}
          target="_blank"
          rel="noreferrer"
          className="text-sky-400 underline"
        />
      );
    },
  };

  return (
    <main className="flex-1 overflow-y-auto p-6 text-white/90 min-w-0">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs text-white/50 font-mono truncate">
          {page.path}
        </div>
        <button
          onClick={() => setShowRaw((r) => !r)}
          className="text-[10px] text-white/40 hover:text-white underline font-mono"
        >
          {showRaw ? "rendered" : "raw"}
        </button>
      </div>
      {!showRaw && Object.keys(page.frontmatter).length > 0 && (
        <details
          open
          className="mb-4 border border-white/10 rounded p-2 text-xs font-mono bg-black/30"
        >
          <summary className="cursor-pointer text-white/60">
            frontmatter
          </summary>
          <pre className="text-white/70 mt-2 whitespace-pre-wrap">
            {JSON.stringify(page.frontmatter, null, 2)}
          </pre>
        </details>
      )}
      {showRaw ? (
        <pre className="text-xs whitespace-pre-wrap text-white/70 font-mono border border-white/10 rounded p-3 bg-black/30">
          {page.raw}
        </pre>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            components={components as any}
          >
            {page.body}
          </ReactMarkdown>
        </div>
      )}
    </main>
  );
}
