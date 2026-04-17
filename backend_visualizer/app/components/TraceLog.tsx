"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type LogCategory = "all" | "assessment" | "graph" | "curiosity" | "research";

type LogLine = {
  id: number;
  ts: string;
  category: Exclude<LogCategory, "all">;
  text: string;
};

let _lineId = 0;

function categorize(stage: string): Exclude<LogCategory, "all"> {
  const s = stage.toLowerCase();
  if (s.includes("graph") || s.includes("node") || s.includes("edge") || s.includes("ingest")) return "graph";
  if (s.includes("assess") || s.includes("profile") || s.includes("anon") || s.includes("redact")) return "assessment";
  if (s.includes("curiosity") || s.includes("score")) return "curiosity";
  if (s.includes("research") || s.includes("enrich") || s.includes("openalex") || s.includes("paper")) return "research";
  return "graph";
}

function makeLogLine(stage: string, student: string, prev: string): LogLine | null {
  if (!stage || stage === prev) return null;
  const cat = categorize(stage);
  const stageLabel = stage.replace(/_/g, " ");
  const now = new Date();
  const ts = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}.${now.getMilliseconds().toString().padStart(3, "0")}`;

  let text = `[${cat}] ${stageLabel}`;
  if (student && student !== "—") text += ` · ${student}`;

  return { id: _lineId++, ts, category: cat, text };
}

const CAT_COLORS: Record<Exclude<LogCategory, "all">, string> = {
  graph: "#00D8FF",
  assessment: "#3FB950",
  curiosity: "#F2C94C",
  research: "#79C0FF",
};

const FILTER_CHIPS: LogCategory[] = ["all", "assessment", "graph", "curiosity", "research"];

function colorForLine(line: LogLine): string {
  if (line.text.includes("ERROR")) return "#EB5757";
  return CAT_COLORS[line.category] || "#8B949E";
}

export function TraceLog() {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [filter, setFilter] = useState<LogCategory>("all");
  const [prevStage, setPrevStage] = useState<string>("");
  const [rate, setRate] = useState<number>(0);
  const [rateCount, setRateCount] = useState<number>(0);
  const [rateTick, setRateTick] = useState<number>(Date.now());
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    const tick = async () => {
      try {
        const overview = await api.demoOverview() as { runtime?: { current_stage?: string; current_student?: string } };
        const stage = overview?.runtime?.current_stage || "";
        const student = overview?.runtime?.current_student || "—";

        const line = makeLogLine(stage, student, prevStage);
        if (line) {
          setPrevStage(stage);
          setRateCount(c => {
            const now = Date.now();
            const elapsed = (now - rateTick) / 1000;
            if (elapsed >= 1) {
              setRate(parseFloat((c / elapsed).toFixed(1)));
              setRateTick(now);
              return 1;
            }
            return c + 1;
          });
          setLines(prev => {
            const next = [...prev, line];
            return next.length > 200 ? next.slice(-200) : next;
          });
        }
      } catch {
        const errLine: LogLine = {
          id: _lineId++,
          ts: new Date().toISOString().slice(11, 23),
          category: "assessment",
          text: "ERROR: /api/demo/overview unreachable",
        };
        setLines(prev => {
          const next = [...prev, errLine];
          return next.length > 200 ? next.slice(-200) : next;
        });
      }
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused, prevStage]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines, paused]);

  const visible = filter === "all" ? lines : lines.filter(l => l.category === filter);

  return (
    <div className="flex flex-col rounded bg-zinc-950 border border-white/10 overflow-hidden" style={{ height: 280 }}>
      {/* Header */}
      <div className="flex items-center gap-3 px-3 py-2 border-b border-white/10 shrink-0">
        <span className="font-mono text-[11px] text-white/60 shrink-0">
          Trace Log · Node+Edge Events
        </span>
        <div className="flex items-center gap-1 flex-1">
          {FILTER_CHIPS.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`font-mono text-[10px] px-2 py-0.5 rounded transition-colors ${
                filter === cat
                  ? "bg-white/15 text-white"
                  : "text-white/30 hover:text-white/60 hover:bg-white/5"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-mono text-[10px] text-white/30">
            Log:{rate}/sec
          </span>
          <button
            onClick={() => setPaused(p => !p)}
            className={`font-mono text-[10px] px-2 py-0.5 rounded border transition-colors ${
              paused
                ? "border-amber-500/50 text-amber-400 bg-amber-500/10"
                : "border-white/10 text-white/40 hover:border-white/20"
            }`}
          >
            {paused ? "RESUME" : "PAUSE"}
          </button>
        </div>
      </div>

      {/* Log body */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2 space-y-0.5"
        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 11 }}
      >
        {visible.length === 0 && (
          <div className="text-white/20 font-mono text-[11px] p-2">
            waiting for agent activity…
          </div>
        )}
        {visible.map(line => (
          <div
            key={line.id}
            className="flex items-start gap-2 hover:bg-white/5 rounded px-1 py-px"
          >
            <span className="text-white/25 shrink-0 w-[88px]">{line.ts}</span>
            <span
              style={{
                color: colorForLine(line),
                fontWeight: line.text.includes("ERROR") ? 700 : 400,
              }}
              className="break-all"
            >
              {line.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
