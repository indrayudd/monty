"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { CuriosityEventsStream } from "../components/CuriosityEventsStream";
import { IngestionWidget } from "../components/IngestionWidget";
import { NotesPipelineWidget } from "../components/NotesPipelineWidget";
import { StatusCards } from "../components/StatusCards";
import { TraceLog } from "../components/TraceLog";

const NAV_LINKS = [
  { href: "/", label: "Live" },
  { href: "/wiki", label: "Wiki" },
  { href: "/console", label: "Console" },
  { href: "/god-mode", label: "God Mode" },
];

function BottomBar({ filter, onFilterChange }: { filter: string; onFilterChange: (v: string) => void }) {
  const pathname = usePathname();
  return (
    <footer className="h-11 border-t border-white/10 bg-black shrink-0 flex items-center px-3 gap-3">
      <nav className="flex gap-0.5">
        {NAV_LINKS.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`font-mono text-[11px] px-2.5 py-1 rounded transition-colors ${
                active
                  ? "bg-white/10 text-white"
                  : "text-white/40 hover:text-white/70 hover:bg-white/5"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="flex-1 flex items-center gap-2">
        <input
          type="text"
          placeholder="filter log…"
          value={filter}
          onChange={e => onFilterChange(e.target.value)}
          className="h-6 px-2 bg-zinc-900 border border-white/10 rounded font-mono text-[11px] text-white/70 placeholder:text-white/20 focus:outline-none focus:border-white/20 w-48"
        />
      </div>
      <button className="font-mono text-[10px] px-3 py-1 rounded border border-amber-500/40 text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 transition-colors shrink-0">
        PAUSE STREAM
      </button>
    </footer>
  );
}

export default function ConsolePage() {
  const [filterText, setFilterText] = useState("");

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col overflow-hidden">
      {/* Main scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Ingestion pipeline stats */}
        <IngestionWidget />

        {/* Notes pipeline */}
        <NotesPipelineWidget />

        {/* Section 1: Status Cards */}
        <StatusCards />

        {/* Section 2: Trace Log */}
        <TraceLog />

        {/* Section 3: Curiosity + Research Stream */}
        <section>
          <div className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2 px-1">
            Curiosity + Research Stream
          </div>
          <CuriosityEventsStream />
        </section>
      </div>

      {/* Bottom Bar */}
      <BottomBar filter={filterText} onFilterChange={setFilterText} />
    </div>
  );
}
