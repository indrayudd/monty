"use client";
import { useEffect, useMemo, useState } from "react";
import { api, type WikiTreeFile } from "../lib/api";

type Node = {
  name: string;
  path?: string;
  mtime?: number;
  children?: Node[];
};

function buildTree(files: WikiTreeFile[]): Node {
  const root: Node = { name: "wiki", children: [] };
  for (const f of files) {
    const parts = f.path.split("/");
    let cur = root;
    parts.forEach((part, i) => {
      const isFile = i === parts.length - 1;
      const next = (cur.children = cur.children || []);
      let child = next.find((n) => n.name === part);
      if (!child) {
        child = isFile
          ? { name: part, path: f.path, mtime: f.mtime }
          : { name: part, children: [] };
        next.push(child);
      }
      cur = child;
    });
  }
  // Sort: folders before files, alphabetical within each.
  const sort = (n: Node) => {
    if (n.children) {
      n.children.sort((a, b) => {
        const af = !!a.children,
          bf = !!b.children;
        if (af !== bf) return af ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      n.children.forEach(sort);
    }
  };
  sort(root);
  return root;
}

function NodeView({
  node,
  onSelect,
  selected,
  depth,
}: {
  node: Node;
  onSelect: (p: string) => void;
  selected: string | null;
  depth: number;
}) {
  const [open, setOpen] = useState(depth < 1);
  if (node.children) {
    return (
      <div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-left w-full font-mono"
          style={{ fontSize: 10, letterSpacing: "1.2px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}
        >
          {open ? "▾" : "▸"} {node.name}
        </button>
        {open && (
          <div className="pl-3">
            {node.children.map((c) => (
              <NodeView
                key={c.name}
                node={c}
                onSelect={onSelect}
                selected={selected}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
  const nowSeconds = Date.now() / 1000;
  const ago = node.mtime ? nowSeconds - node.mtime : Infinity;
  const cls =
    ago < 30
      ? "bg-emerald-500/20 animate-pulse"
      : ago < 300
        ? "bg-emerald-500/10"
        : "";
  return (
    <button
      onClick={() => node.path && onSelect(node.path)}
      className={`block w-full text-left text-xs px-1 py-0.5 rounded font-mono ${cls} ${
        selected === node.path
          ? "text-white bg-white/10"
          : "text-white/60 hover:text-white"
      }`}
    >
      {node.name}
    </button>
  );
}

export function WikiFileTree({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (p: string) => void;
}) {
  const [files, setFiles] = useState<WikiTreeFile[]>([]);
  const [filter, setFilter] = useState("");
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.wikiTree();
        setFiles(r.files || []);
        setDegraded(false);
      } catch {
        setDegraded(true);
      }
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, []);

  const filtered = useMemo(
    () => files.filter((f) => !filter || f.path.includes(filter)),
    [files, filter],
  );

  // Split top-level files (no slash) above folders.
  const topFiles = useMemo(
    () => filtered.filter((f) => !f.path.includes("/")),
    [filtered],
  );
  const nested = useMemo(
    () => filtered.filter((f) => f.path.includes("/")),
    [filtered],
  );
  const tree = useMemo(() => buildTree(nested), [nested]);

  return (
    <aside className="w-[300px] shrink-0 border-r border-white/10 bg-zinc-950 overflow-y-auto">
      <div className="px-2 pt-2 pb-1" style={{ fontSize: 10, letterSpacing: "1.2px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>FILES</div>
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="filter…"
        className="w-full bg-zinc-900 px-2 py-1.5 text-xs border-b border-white/10 text-white font-mono outline-none"
      />
      <div className="p-2 space-y-0.5">
        {degraded && (
          <div className="text-[10px] text-amber-300/80 font-mono mb-2">
            ⚠ wiki-tree unreachable — retry pending
          </div>
        )}
        {files.length === 0 && !degraded && (
          <div className="text-[11px] text-white/30 font-mono">
            (empty — the agent has not yet written any markdown)
          </div>
        )}
        {topFiles.map((f) => {
          const nowSeconds = Date.now() / 1000;
          const ago = f.mtime ? nowSeconds - f.mtime : Infinity;
          const cls =
            ago < 30
              ? "bg-emerald-500/20 animate-pulse"
              : ago < 300
                ? "bg-emerald-500/10"
                : "";
          return (
            <button
              key={f.path}
              onClick={() => onSelect(f.path)}
              className={`block w-full text-left text-xs px-1 py-0.5 rounded font-mono ${cls} ${
                selected === f.path
                  ? "text-white bg-white/10"
                  : "text-white/70 hover:text-white"
              }`}
            >
              {f.path}
            </button>
          );
        })}
        {topFiles.length > 0 && nested.length > 0 && (
          <div className="border-t border-white/5 my-1" />
        )}
        {tree.children?.map((c) => (
          <NodeView
            key={c.name}
            node={c}
            onSelect={onSelect}
            selected={selected}
            depth={0}
          />
        ))}
      </div>
    </aside>
  );
}
