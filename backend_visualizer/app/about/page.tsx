"use client";

function PipelineDiagram() {
  const stages = [
    { id: "persona", label: "Persona Engine", sub: "generates observation via LLM", color: "#a855f7" },
    { id: "streamer", label: "Streamer", sub: "inserts into ingested_observations", color: "#8b5cf6" },
    { id: "assess", label: "Behavioral Assessment", sub: "LLM extracts severity + facets", color: "#3b82f6" },
    { id: "extract", label: "Node Extraction", sub: "triggers, behaviors, brain states, responses", color: "#0ea5e9" },
    { id: "wiki", label: "Wiki Writer", sub: "incident page + behavioral KG update", color: "#14b8a6" },
    { id: "profile", label: "Student Profile", sub: "reassess full history, update summary", color: "#22c55e" },
    { id: "curiosity", label: "Curiosity Gate", sub: "score novelty, recurrence, surprise", color: "#eab308" },
    { id: "research", label: "Research Fetch", sub: "OpenAlex papers if score \u{2265} 0.70", color: "#f97316" },
    { id: "alert", label: "Alert Generation", sub: "recommended actions for educators", color: "#ef4444" },
  ];

  const idle = { id: "idle", label: "Idle Research", sub: "discover edges between disconnected nodes", color: "#6b7280" };

  return (
    <div className="my-6">
      <div className="flex flex-col items-center gap-0">
        {stages.map((s, i) => (
          <div key={s.id} className="flex flex-col items-center">
            {/* Node */}
            <div
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg border w-full max-w-md"
              style={{ borderColor: s.color + "40", background: s.color + "08" }}
            >
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: s.color }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-white/90">{s.label}</div>
                <div className="text-[11px] font-mono text-white/40">{s.sub}</div>
              </div>
              <div className="text-[10px] font-mono text-white/20 shrink-0">{i + 1}</div>
            </div>
            {/* Arrow */}
            {i < stages.length - 1 && (
              <div className="flex flex-col items-center py-0.5">
                <div className="w-px h-3 bg-white/15" />
                <div className="text-white/15 text-[8px] leading-none">&#x25BC;</div>
              </div>
            )}
          </div>
        ))}

        {/* Branch to idle */}
        <div className="flex items-start gap-4 mt-4 w-full max-w-md">
          <div className="flex-1 border-t border-white/10 pt-3">
            <div className="text-[10px] font-mono text-white/30 uppercase tracking-wider mb-2 text-center">
              during idle cycles
            </div>
            <div
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg border"
              style={{ borderColor: idle.color + "40", background: idle.color + "08" }}
            >
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: idle.color }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-white/90">{idle.label}</div>
                <div className="text-[11px] font-mono text-white/40">{idle.sub}</div>
              </div>
              <div className="text-[10px] font-mono text-white/20 shrink-0">10</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white flex justify-center">
      <div className="max-w-2xl w-full px-6 py-12">

        {/* Hero */}
        <h1 className="text-3xl font-bold tracking-tight mb-2">Monty</h1>
        <p className="text-lg text-white/60 font-mono mb-10">
          Autonomous behavioral intelligence for early childhood classrooms
        </p>

        {/* What this is */}
        <section className="mb-10">
          <h2 className="text-sm font-mono text-amber-400/80 uppercase tracking-wider mb-3">
            What this is
          </h2>
          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            Monty is an AI agent that watches a Montessori classroom through
            teacher observation notes and builds a living, growing knowledge
            base of what it learns. Every note that arrives triggers a full
            reassessment: the agent reads the child's history, extracts
            behavioral patterns, updates a shared knowledge graph, and decides
            whether it needs to go find research papers to fill gaps in its
            understanding.
          </p>
          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            The knowledge graph is the core. Behavioral patterns like
            "frustration after error correction" or "peer-recruiting during
            sensory play" emerge as nodes that grow stronger with each
            supporting observation. Edges form between them as the agent
            discovers relationships. When enough children exhibit a pattern,
            or when something surprising appears, a curiosity gate fires and
            the agent autonomously searches OpenAlex for peer-reviewed
            literature to ground its observations in science.
          </p>
          <p className="text-[15px] leading-relaxed text-white/80">
            Everything the agent knows lives in markdown files on disk. The
            database is a derived index that can be rebuilt at any time from
            those files. This means the agent's knowledge is human-readable,
            version-controlled, and auditable down to a single observation.
          </p>
        </section>

        {/* What you're looking at */}
        <section className="mb-10">
          <h2 className="text-sm font-mono text-amber-400/80 uppercase tracking-wider mb-3">
            What you're looking at
          </h2>
          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            This dashboard makes the agent's work visible in real time. You
            can watch behavioral patterns emerge as the force-directed
            knowledge graph grows on the Live page, read the actual markdown
            the agent writes on the Wiki page, and trace every processing
            step on the Console.
          </p>
          <div className="grid grid-cols-2 gap-3 my-6">
            {[
              {
                label: "Live",
                desc: "Force-directed behavioral graph, student timelines, and the agent pipeline stage rail. The operational view.",
              },
              {
                label: "Wiki",
                desc: "File-tree browser of the markdown knowledge base, inspired by Andrej Karpathy's LLM-wiki concept. Every behavioral node, student incident, and research paper the agent has written, browsable with backlinks and graph connections.",
              },
              {
                label: "Console",
                desc: "Cycle state, throughput metrics, trace logs, and the curiosity event stream. The diagnostic view.",
              },
              {
                label: "God Mode",
                desc: "Full operator control. Steer persona sliders, inject scenarios, trigger story presets, adjust curiosity sensitivity, and purge-restart the entire system.",
              },
            ].map((item) => (
              <div
                key={item.label}
                className="border border-white/10 rounded-lg p-3 bg-zinc-900/60"
              >
                <div className="text-xs font-mono text-white/50 uppercase tracking-wider mb-1">
                  {item.label}
                </div>
                <div className="text-[13px] text-white/70 leading-snug">
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* The personas */}
        <section className="mb-10">
          <h2 className="text-sm font-mono text-amber-400/80 uppercase tracking-wider mb-3">
            The simulated classroom
          </h2>
          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            Five synthetic children attend this classroom, each with a
            distinct temperament and stress response profile. A persona
            engine generates observation notes through an LLM, producing
            realistic Montessori-style documentation that varies with each
            child's current regulatory state.
          </p>
          <p className="text-[15px] leading-relaxed text-white/80">
            Operators can adjust each child's regulatory slider from calm to
            dysregulated, change their stress response type, inject specific
            scenarios (a calm morning, an escalation, an emergency), and
            force peer interactions between children. The agent processes
            whatever comes through the pipeline and responds accordingly.
          </p>
        </section>

        {/* Why this matters */}
        <section className="mb-10">
          <h2 className="text-sm font-mono text-amber-400/80 uppercase tracking-wider mb-3">
            Why this matters
          </h2>
          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            Early childhood teachers spend an estimated 8-12 hours per week
            on documentation and pattern recognition across their classroom.
            Monty eliminates the synthesis layer: reviewing notes, updating
            developmental records, and connecting observations to research.
            That returns 4-6 hours per teacher per week to direct instruction.
          </p>

          <div className="grid grid-cols-2 gap-3 my-6">
            {[
              {
                metric: "Months to minutes",
                desc: "Cross-child pattern recognition that takes 2-3 months of experienced observation surfaces in hours as the knowledge graph grows.",
              },
              {
                metric: "26% annual turnover",
                desc: "Average early childhood teacher turnover rate. Each departure loses months of child context. A persistent wiki eliminates institutional knowledge loss entirely.",
                source: "Center for the Study of Child Care Employment, UC Berkeley, 2020",
              },
              {
                metric: "$5K-$15K per child",
                desc: "Published ROI of early intervention when developmental concerns are identified 3-6 months sooner. Real-time severity tracking and trend alerts accelerate identification.",
                source: "RAND Corporation, \"Investing in Our Children,\" 2005; Heckman, J., \"Skill Formation and the Economics of Investing in Disadvantaged Children,\" Science, 2006",
              },
              {
                metric: "Zero to automatic",
                desc: "Research retrieval that teachers never have time to do. The curiosity gate autonomously fetches peer-reviewed papers from OpenAlex filtered to early childhood education topics.",
              },
            ].map((item) => (
              <div
                key={item.metric}
                className="border border-white/10 rounded-lg p-3 bg-zinc-900/60"
              >
                <div className="text-sm font-semibold text-white/90 mb-1">
                  {item.metric}
                </div>
                <div className="text-[12px] text-white/60 leading-snug">
                  {item.desc}
                </div>
                {item.source && (
                  <div className="text-[10px] text-white/30 mt-1.5 font-mono leading-snug">
                    {item.source}
                  </div>
                )}
              </div>
            ))}
          </div>

          <p className="text-[15px] leading-relaxed text-white/80 mb-4">
            This scales to organizations. A single classroom has 25 children.
            A school district has thousands. The same architecture maintains
            a unified, queryable knowledge base across all of them. Any
            authorized educator can ask "which children showed regression this
            month?" and get an answer grounded in aggregated observations,
            linked behavioral patterns, and cited literature.
          </p>
          <p className="text-[15px] leading-relaxed text-white/80">
            The compound effect is the hardest to quantify and the most
            valuable. After a year of operation, the knowledge graph contains
            thousands of observations, hundreds of behavioral patterns, and
            dozens of research links. That institutional knowledge asset has
            no equivalent in a paper-based system.
          </p>
        </section>

        {/* Pipeline */}
        <section className="mb-10">
          <h2 className="text-sm font-mono text-amber-400/80 uppercase tracking-wider mb-3">
            How it works
          </h2>
          <PipelineDiagram />
        </section>

        {/* Built for */}
        <section className="mb-6">
          <div className="text-[13px] text-white/40 font-mono">
            Pushing the frontiers for Harnesses
          </div>
          <div className="text-[13px] text-white/30 font-mono mt-1">
            Python + FastAPI + Next.js + SQLite + OpenAI + OpenAlex
          </div>
        </section>

      </div>
    </div>
  );
}
