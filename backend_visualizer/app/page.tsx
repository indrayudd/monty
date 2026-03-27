"use client";

import { useEffect, useMemo, useState } from "react";

type StudentProfile = {
  student_name: string;
  current_severity: string;
  previous_severity: string | null;
  trend: string;
  assessment_count: number;
  latest_summary: string;
  latest_patterns: string;
  latest_suggestions: string;
  updated_at?: string;
};

type NoteItem = {
  id: number;
  name: string;
  body: string;
  inserted_at?: string;
};

type ActionItem = {
  id: number;
  student_name: string | null;
  note_id: number | null;
  action_kind: string;
  status: string;
  payload: Record<string, unknown>;
  created_at?: string;
};

type AlertItem = {
  id: number;
  student_name: string;
  severity: string;
  title: string;
  body: string;
  recommended_actions: string[];
  status: string;
};

type KnowledgeNode = {
  id: number;
  student_name?: string | null;
  topic: string;
  source_title: string;
  source_url: string;
  related_topics: string[];
  insights: string[];
  confidence: number;
};

type PersonalityFacet = {
  facet_type: string;
  facet_value: string;
  evidence: string;
  confidence: number;
};

type DemoOverview = {
  runtime: Record<string, string | number | boolean>;
  counts: {
    notes: number;
    profiles: number;
    knowledge_nodes: number;
    alerts: number;
    actions: number;
  };
  selected_student: string | null;
  students: StudentProfile[];
  recent_notes: NoteItem[];
  recent_actions: ActionItem[];
  alerts: AlertItem[];
  knowledge_nodes: KnowledgeNode[];
  personality_graphs: Record<string, PersonalityFacet[]>;
  timestamp: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function timeLabel(value?: string | number) {
  if (!value) return "now";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return "now";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function preview(text: string, limit = 150) {
  const compact = text.replace(/\s+/g, " ").trim();
  return compact.length <= limit ? compact : `${compact.slice(0, limit - 3)}...`;
}

function severityTone(severity?: string) {
  switch ((severity || "").toLowerCase()) {
    case "red":
    case "critical":
    case "high":
      return "danger";
    case "yellow":
    case "medium":
      return "warn";
    default:
      return "safe";
  }
}

function groupFacets(facets: PersonalityFacet[]) {
  return {
    personality_trait: facets.filter((facet) => facet.facet_type === "personality_trait"),
    regulation_trigger: facets.filter((facet) => facet.facet_type === "regulation_trigger"),
    support_strategy: facets.filter((facet) => facet.facet_type === "support_strategy"),
    behavioral_pattern: facets.filter((facet) => facet.facet_type === "behavioral_pattern"),
  };
}

export default function Page() {
  const [data, setData] = useState<DemoOverview | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadOverview() {
    const response = await fetch(`${API_BASE}/api/demo/overview`, { cache: "no-store" });
    if (!response.ok) throw new Error(`overview failed: ${response.status}`);
    const next = (await response.json()) as DemoOverview;
    setData(next);
    setSelectedStudent((current) => current || next.selected_student || next.students[0]?.student_name || null);
  }

  async function bootstrap(reset = false) {
    setBootstrapping(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/demo/bootstrap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset }),
      });
      if (!response.ok) throw new Error(`bootstrap failed: ${response.status}`);
      const next = (await response.json()) as DemoOverview;
      setData(next);
      setSelectedStudent(next.selected_student || next.students[0]?.student_name || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bootstrap failed");
    } finally {
      setBootstrapping(false);
    }
  }

  useEffect(() => {
    void bootstrap(false);
  }, []);

  useEffect(() => {
    if (bootstrapping) return;
    const interval = window.setInterval(() => {
      void loadOverview().catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Polling failed");
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [bootstrapping]);

  const activeProfile = useMemo(
    () => data?.students.find((student) => student.student_name === selectedStudent) || data?.students[0] || null,
    [data, selectedStudent],
  );

  const activeFacets = useMemo(() => {
    if (!data || !activeProfile) return [];
    return data.personality_graphs[activeProfile.student_name] || [];
  }, [data, activeProfile]);

  const groupedFacets = useMemo(() => groupFacets(activeFacets), [activeFacets]);

  const notes = data?.recent_notes || [];
  const actions = data?.recent_actions || [];
  const alerts = data?.alerts || [];
  const knowledgeNodes = data?.knowledge_nodes || [];

  return (
    <main className="shell">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />

      <section className="hero">
        <div>
          <p className="eyebrow">Monty Live Backend Visualizer</p>
          <h1>Watch the backend think in public.</h1>
          <p className="lede">
            Notes land every second, the agent re-assesses every two seconds, the personality graph densifies, and the knowledge graph expands only when the model decides it needs more context.
          </p>
        </div>
        <div className="hero-actions">
          <button className="primary" onClick={() => void bootstrap(true)} disabled={bootstrapping}>
            {bootstrapping ? "Starting demo..." : "Restart From Empty"}
          </button>
          <div className="runtime-pill">
            <span className="pulse" />
            {data?.runtime.started ? "Live" : "Waiting"}
            <span>{`notes ${data?.runtime.note_interval_seconds ?? 1}s`}</span>
            <span>{`agent ${data?.runtime.agent_interval_seconds ?? 2}s`}</span>
          </div>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="metrics">
        <Metric title="Notes Ingested" value={data?.counts.notes ?? 0} detail={`Latest ${timeLabel(notes[0]?.inserted_at)}`} />
        <Metric title="Agent Traces" value={data?.counts.actions ?? 0} detail={`Latest ${timeLabel(actions[0]?.created_at)}`} />
        <Metric title="Knowledge Nodes" value={data?.counts.knowledge_nodes ?? 0} detail="OpenAlex-backed memory" />
        <Metric title="Open Alerts" value={data?.counts.alerts ?? 0} detail="Critical states stay visible" />
      </section>

      <section className="workflow-grid">
        <div className="panel tall">
          <PanelHeader
            title="1. Note Ingestion Stream"
            subtitle="Directly from Ghost note rows. Each card is a database insertion the agent can now react to."
          />
          <div className="note-stack">
            {notes.map((note, index) => (
              <article className="note-card" key={note.id} style={{ animationDelay: `${index * 80}ms` }}>
                <div className="note-meta">
                  <span className="note-id">{`#${note.id}`}</span>
                  <span>{note.name}</span>
                  <span>{timeLabel(note.inserted_at)}</span>
                </div>
                <p>{preview(note.body)}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="panel tall">
          <PanelHeader
            title="2. Agent Trace"
            subtitle="This is the live execution log: note ingestion, profile updates, research fetches, and alert creation."
          />
          <div className="trace-list">
            {actions.map((action) => (
              <article className="trace-item" key={action.id}>
                <div className="trace-head">
                  <strong>{action.action_kind.replaceAll("_", " ")}</strong>
                  <span>{timeLabel(action.created_at)}</span>
                </div>
                <p className="trace-student">{action.student_name || "system"}</p>
                <p>{preview(JSON.stringify(action.payload ?? {}, null, 0) || "", 180)}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="panel knowledge-panel">
          <PanelHeader
            title="3. Knowledge Graph Expansion"
            subtitle="Research only appears when the local graph is thin. The graph grows from OpenAlex hits and retained summaries."
          />
          <KnowledgeGraph nodes={knowledgeNodes} />
        </div>
      </section>

      <section className="bottom-grid">
        <div className="panel">
          <PanelHeader
            title="4. Student Personality Graph"
            subtitle="The graph is rebuilt from cumulative notes, not a single observation."
          />
          <div className="student-strip">
            {data?.students.map((student) => (
              <button
                key={student.student_name}
                className={`student-chip tone-${severityTone(student.current_severity)} ${selectedStudent === student.student_name ? "selected" : ""}`}
                onClick={() => setSelectedStudent(student.student_name)}
              >
                <span>{student.student_name}</span>
                <small>{student.current_severity}</small>
              </button>
            ))}
          </div>
          {activeProfile ? (
            <>
              <div className="student-summary">
                <div>
                  <span className={`severity-badge tone-${severityTone(activeProfile.current_severity)}`}>
                    {activeProfile.current_severity}
                  </span>
                  <h2>{activeProfile.student_name}</h2>
                  <p>{activeProfile.latest_summary}</p>
                </div>
                <div className="summary-side">
                  <span>{`${activeProfile.assessment_count} assessments`}</span>
                  <span>{`trend: ${activeProfile.trend}`}</span>
                </div>
              </div>
              <PersonalityGraph studentName={activeProfile.student_name} facets={groupedFacets} />
            </>
          ) : (
            <div className="empty-state">Waiting for the first profile.</div>
          )}
        </div>

        <div className="panel">
          <PanelHeader
            title="5. Live Alerts"
            subtitle="Critical states stay pinned so the workflow reads like an active operating system, not a static report."
          />
          <div className="alert-list">
            {alerts.map((alert) => (
              <article className={`alert-card tone-${severityTone(alert.severity)}`} key={alert.id}>
                <div className="alert-head">
                  <strong>{alert.title}</strong>
                  <span>{alert.student_name}</span>
                </div>
                <p>{preview(alert.body)}</p>
                <ul>
                  {alert.recommended_actions.slice(0, 3).map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ title, value, detail }: { title: string; value: number; detail: string }) {
  return (
    <article className="metric-card">
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="panel-header">
      <div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
      </div>
    </header>
  );
}

function KnowledgeGraph({ nodes }: { nodes: KnowledgeNode[] }) {
  const graphNodes = nodes.slice(0, 12);
  const centerX = 280;
  const centerY = 200;
  const radius = 140;

  return (
    <div className="graph-shell">
      <svg viewBox="0 0 560 400" className="graph-svg" role="img" aria-label="Knowledge graph">
        <defs>
          <linearGradient id="edge" x1="0%" x2="100%" y1="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(92,226,194,0.85)" />
            <stop offset="100%" stopColor="rgba(255,165,84,0.4)" />
          </linearGradient>
        </defs>

        <circle cx={centerX} cy={centerY} r={66} className="graph-core" />
        <text x={centerX} y={centerY - 4} textAnchor="middle" className="graph-core-label">
          Monty Agent
        </text>
        <text x={centerX} y={centerY + 18} textAnchor="middle" className="graph-core-sub">
          OpenAlex memory
        </text>

        {graphNodes.map((node, index) => {
          const angle = (Math.PI * 2 * index) / Math.max(graphNodes.length, 1) - Math.PI / 2;
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          const size = 18 + (node.confidence || 0.5) * 16;
          return (
            <g key={node.id}>
              <line x1={centerX} y1={centerY} x2={x} y2={y} stroke="url(#edge)" strokeWidth="2" />
              <circle cx={x} cy={y} r={size} className="graph-node" />
              <text x={x} y={y + 4} textAnchor="middle" className="graph-node-label">
                {index + 1}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="graph-legend">
        {graphNodes.map((node) => (
          <article className="legend-card" key={node.id}>
            <strong>{node.source_title}</strong>
            <p>{preview(node.insights?.[0] || node.topic, 120)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function PersonalityGraph({
  studentName,
  facets,
}: {
  studentName: string;
  facets: ReturnType<typeof groupFacets>;
}) {
  const groups = [
    { key: "personality_trait", label: "Traits", x: 130, y: 90, values: facets.personality_trait },
    { key: "regulation_trigger", label: "Triggers", x: 430, y: 90, values: facets.regulation_trigger },
    { key: "support_strategy", label: "Supports", x: 130, y: 290, values: facets.support_strategy },
    { key: "behavioral_pattern", label: "Patterns", x: 430, y: 290, values: facets.behavioral_pattern },
  ];

  return (
    <div className="graph-shell">
      <svg viewBox="0 0 560 380" className="graph-svg" role="img" aria-label="Personality graph">
        <circle cx={280} cy={190} r={62} className="person-core" />
        <text x={280} y={186} textAnchor="middle" className="graph-core-label">
          {studentName.split(" ")[0]}
        </text>
        <text x={280} y={208} textAnchor="middle" className="graph-core-sub">
          personality graph
        </text>

        {groups.map((group) => (
          <g key={group.key}>
            <line x1={280} y1={190} x2={group.x} y2={group.y} className="person-edge" />
            <circle cx={group.x} cy={group.y} r={34} className="person-group" />
            <text x={group.x} y={group.y + 4} textAnchor="middle" className="graph-node-label small">
              {group.label}
            </text>
            {group.values.slice(0, 3).map((facet, index) => {
              const offsetX = group.x + (index - 1) * 64;
              const offsetY = group.y + (group.y < 190 ? -58 : 58);
              return (
                <g key={`${group.key}-${facet.facet_value}`}>
                  <line x1={group.x} y1={group.y} x2={offsetX} y2={offsetY} className="person-edge faint" />
                  <rect x={offsetX - 54} y={offsetY - 18} width={108} height={36} rx={18} className="facet-pill" />
                  <text x={offsetX} y={offsetY + 4} textAnchor="middle" className="facet-label">
                    {preview(facet.facet_value, 20)}
                  </text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
    </div>
  );
}
