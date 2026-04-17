"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type RuntimeStatus = {
  current_stage?: string;
  current_student?: string;
  notes_per_second?: number;
  students_processing?: number;
  [k: string]: unknown;
};

type GraphCounts = {
  nodes: number;
  edges: number;
  studentsCount: number;
};

const STAGES = ["ingest", "assess", "profile", "enrich"] as const;

function getStageIndex(stage: string): number {
  const s = stage.toLowerCase();
  if (s.includes("ingest") || s.includes("note")) return 0;
  if (s.includes("assess") || s.includes("reassess")) return 1;
  if (s.includes("profile") || s.includes("student")) return 2;
  if (s.includes("enrich") || s.includes("research") || s.includes("curiosity")) return 3;
  return -1;
}

export function StatusCards() {
  const [runtime, setRuntime] = useState<RuntimeStatus>({});
  const [graph, setGraph] = useState<GraphCounts>({ nodes: 0, edges: 0, studentsCount: 0 });
  const [prevStage, setPrevStage] = useState<string>("");
  const [notesPerSec, setNotesPerSec] = useState<number>(0);
  const [lastTick, setLastTick] = useState<number>(Date.now());
  const [noteCount, setNoteCount] = useState<number>(0);

  useEffect(() => {
    const tick = async () => {
      try {
        const [overview, bgraph] = await Promise.all([
          api.demoOverview() as Promise<{ runtime?: RuntimeStatus }>,
          api.behavioralGraph(1),
        ]);
        const rt = overview?.runtime || {};
        setRuntime(rt);

        const stage = rt.current_stage || "";
        if (stage !== prevStage) {
          const now = Date.now();
          const elapsed = (now - lastTick) / 1000;
          if (elapsed > 0) setNotesPerSec(parseFloat((1 / elapsed).toFixed(2)));
          setPrevStage(stage);
          setLastTick(now);
          setNoteCount(c => c + 1);
        }

        const studentSet = new Set(bgraph.nodes.map(n => n.students_count));
        const avgStudents = bgraph.nodes.length > 0
          ? bgraph.nodes.reduce((a, n) => a + n.students_count, 0) / bgraph.nodes.length
          : 0;
        setGraph({
          nodes: bgraph.nodes.length,
          edges: bgraph.edges.length,
          studentsCount: Math.round(avgStudents),
        });
      } catch {
        // silently degrade
      }
    };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prevStage, lastTick]);

  const stage = runtime.current_stage || "idle";
  const student = runtime.current_student || "—";
  const activeStageIdx = getStageIndex(stage);

  return (
    <div className="grid grid-cols-3 gap-3">
      {/* Cycle State */}
      <div className="rounded bg-zinc-950 border border-white/10 border-l-2 border-l-blue-500 p-3 flex flex-col gap-2">
        <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider">Cycle State</div>
        <div className="flex items-center gap-0 font-mono text-[11px]">
          {STAGES.map((s, i) => (
            <span key={s} className="flex items-center">
              <span className={i === activeStageIdx ? "text-blue-400 font-semibold" : "text-white/30"}>
                {s}
              </span>
              {i < STAGES.length - 1 && (
                <span className="text-white/20 mx-1">&gt;</span>
              )}
            </span>
          ))}
        </div>
        <div className="font-mono text-[10px] text-white/40 truncate">
          &gt; {student}
        </div>
        <div className="font-mono text-[10px] text-blue-300/70 truncate">
          {stage.replace(/_/g, " ") || "idle"}
        </div>
      </div>

      {/* Graph State */}
      <div className="rounded bg-zinc-950 border border-white/10 border-l-2 border-l-cyan-400 p-3 flex flex-col gap-2">
        <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider">Graph State</div>
        <div className="grid grid-cols-3 gap-1 mt-1">
          <div className="text-center">
            <div className="font-mono text-lg text-cyan-400 font-semibold leading-none">{graph.nodes}</div>
            <div className="font-mono text-[9px] text-white/40 mt-0.5">nodes</div>
          </div>
          <div className="text-center">
            <div className="font-mono text-lg text-cyan-300 font-semibold leading-none">{graph.edges}</div>
            <div className="font-mono text-[9px] text-white/40 mt-0.5">edges</div>
          </div>
          <div className="text-center">
            <div className="font-mono text-lg text-cyan-200 font-semibold leading-none">{graph.studentsCount}</div>
            <div className="font-mono text-[9px] text-white/40 mt-0.5">avg/node</div>
          </div>
        </div>
        <div className="font-mono text-[10px] text-white/30 mt-auto">behavioral knowledge graph</div>
      </div>

      {/* Throughput */}
      <div className="rounded bg-zinc-950 border border-white/10 border-l-2 border-l-emerald-500 p-3 flex flex-col gap-2">
        <div className="text-[10px] font-mono text-white/50 uppercase tracking-wider">Throughput</div>
        <div className="flex flex-col gap-1.5 mt-1">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-xl text-emerald-400 font-semibold leading-none">
              {notesPerSec.toFixed(2)}
            </span>
            <span className="font-mono text-[10px] text-white/40">notes/sec</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-xl text-emerald-300 font-semibold leading-none">
              {noteCount}
            </span>
            <span className="font-mono text-[10px] text-white/40">cycles total</span>
          </div>
        </div>
        <div className="font-mono text-[10px] text-emerald-400/50 mt-auto">
          {stage !== "idle" ? "● processing" : "○ idle"}
        </div>
      </div>
    </div>
  );
}
