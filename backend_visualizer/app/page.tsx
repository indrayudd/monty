"use client";

import type { ReactNode } from "react";
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

type WorkflowStep = {
  key: string;
  label: string;
  detail: string;
  at?: string;
  status: "active" | "ready" | "idle";
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const LIVE_WINDOW_MS = 6500;

function timeLabel(value?: string | number) {
  if (!value) return "now";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return "now";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function relativeLabel(value?: string | number) {
  if (!value) return "now";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  const deltaSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (deltaSeconds < 2) return "just now";
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
  const minutes = Math.round(deltaSeconds / 60);
  return `${minutes}m ago`;
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

function titleCase(input: string) {
  return input
    .replaceAll("_", " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item)).filter(Boolean);
}

function numberValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isFresh(at?: string) {
  if (!at) return false;
  const date = new Date(at);
  if (Number.isNaN(date.getTime())) return false;
  return Date.now() - date.getTime() <= LIVE_WINDOW_MS;
}

function groupFacets(facets: PersonalityFacet[]) {
  return {
    personality_trait: facets.filter((facet) => facet.facet_type === "personality_trait"),
    regulation_trigger: facets.filter((facet) => facet.facet_type === "regulation_trigger"),
    support_strategy: facets.filter((facet) => facet.facet_type === "support_strategy"),
    behavioral_pattern: facets.filter((facet) => facet.facet_type === "behavioral_pattern"),
  };
}

function latestAction(actions: ActionItem[], kind: string) {
  return actions.find((action) => action.action_kind === kind) || null;
}

function runtimeString(value: string | number | boolean | undefined) {
  return value == null ? "" : String(value);
}

function runtimeStarted(runtime: Record<string, string | number | boolean> | undefined) {
  return runtime?.started === true || runtime?.demo_started === "1";
}

function workflowStepKey(stage: string, hasQueries: boolean, hasAlert: boolean): WorkflowStep["key"] | null {
  switch (stage) {
    case "ingesting_note":
    case "note_ingested":
      return "ingest";
    case "reassessing_student":
    case "updating_profile":
      return "assess";
    case "enriching_knowledge":
      return "enrich";
    case "writing_alert":
      return "alert";
    case "cycle_complete":
      if (hasAlert) return "alert";
      if (hasQueries) return "enrich";
      return "assess";
    default:
      return null;
  }
}

export default function Page() {
  const [data, setData] = useState<DemoOverview | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadOverview() {
    const response = await fetch(`${API_BASE}/api/demo/overview`, { cache: "no-store" });
    if (!response.ok) throw new Error(`overview failed: ${response.status}`);
    const next = (await response.json()) as DemoOverview;
    setData(next);
    setSelectedStudent((current) => current || next.selected_student || next.students[0]?.student_name || null);
  }

  async function startDemo(reset = true) {
    setBootstrapping(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/demo/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset }),
      });
      if (!response.ok) throw new Error(`start failed: ${response.status}`);
      const next = (await response.json()) as DemoOverview;
      setData(next);
      setSelectedStudent(next.selected_student || next.students[0]?.student_name || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo start failed");
    } finally {
      setBootstrapping(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    void loadOverview()
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Initial load failed");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (loading || bootstrapping) return;
    const interval = window.setInterval(() => {
      void loadOverview().catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Polling failed");
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [bootstrapping, loading]);

  const notes = data?.recent_notes || [];
  const actions = data?.recent_actions || [];
  const alerts = data?.alerts || [];
  const knowledgeNodes = data?.knowledge_nodes || [];
  const isRunning = runtimeStarted(data?.runtime);
  const runtimeMode = runtimeString(data?.runtime.mode) || (isRunning ? "running" : "idle");

  const activeProfile = useMemo(
    () => data?.students.find((student) => student.student_name === selectedStudent) || data?.students[0] || null,
    [data, selectedStudent],
  );

  const activeFacets = useMemo(() => {
    if (!data || !activeProfile) return [];
    return data.personality_graphs[activeProfile.student_name] || [];
  }, [data, activeProfile]);

  const groupedFacets = useMemo(() => groupFacets(activeFacets), [activeFacets]);

  const liveSummary = useMemo(() => {
    const runtime = data?.runtime;
    const noteAction = latestAction(actions, "note_ingested");
    const agentAction = latestAction(actions, "agent_cycle");
    const cycleSummary = latestAction(actions, "cycle_summary");
    const runtimeStage = runtimeString(runtime?.current_stage);
    const runtimeStudent = runtimeString(runtime?.current_student);
    const runtimeMessage = runtimeString(runtime?.stage_message);
    const runtimeStageAt = runtimeString(runtime?.stage_started_at);
    const queries = stringList(agentAction?.payload?.queries);
    const newNodes = numberValue(agentAction?.payload?.new_nodes_created);
    const severity = String(agentAction?.payload?.severity || activeProfile?.current_severity || "green");
    const trend = String(agentAction?.payload?.trend || activeProfile?.trend || "stable");
    const alertTitle = String(agentAction?.payload?.alert_title || "");
    const cycleNotes = numberValue(cycleSummary?.payload?.new_notes);
    const processedStudents = numberValue(cycleSummary?.payload?.students_processed);
    const currentStudent = runtimeStudent || agentAction?.student_name || noteAction?.student_name || selectedStudent;
    const activeStepKey = workflowStepKey(runtimeStage, queries.length > 0, Boolean(alertTitle));
    const stepOrder: WorkflowStep["key"][] = ["ingest", "assess", "enrich", "alert"];
    const activeStepIndex = activeStepKey ? stepOrder.indexOf(activeStepKey) : -1;
    const shouldShowCompletedState =
      isRunning && (notes.length > 0 || Boolean(agentAction) || runtimeStage === "cycle_complete" || runtimeStage === "waiting_for_note");

    function stepStatus(key: WorkflowStep["key"]) {
      if (!isRunning) return "idle";
      if (activeStepIndex >= 0) {
        const index = stepOrder.indexOf(key);
        if (index < activeStepIndex) return "ready";
        if (index === activeStepIndex) return "active";
        return "idle";
      }
      return shouldShowCompletedState ? "ready" : "idle";
    }

    const steps: WorkflowStep[] = [
      {
        key: "ingest",
        label: "Ingest",
        detail:
          activeStepKey === "ingest" && runtimeMessage
            ? runtimeMessage
            : noteAction
              ? `${noteAction.student_name || "Student"} note inserted`
              : "Waiting for the first note row",
        at: activeStepKey === "ingest" ? runtimeStageAt || noteAction?.created_at : noteAction?.created_at,
        status: stepStatus("ingest"),
      },
      {
        key: "assess",
        label: "Reassess",
        detail:
          activeStepKey === "assess" && runtimeMessage
            ? runtimeMessage
            : agentAction
              ? `${agentAction.student_name || "System"} moved to ${severity} / ${trend}`
              : "No active reassessment yet",
        at: activeStepKey === "assess" ? runtimeStageAt || agentAction?.created_at : agentAction?.created_at,
        status: stepStatus("assess"),
      },
      {
        key: "enrich",
        label: "Enrich",
        detail:
          activeStepKey === "enrich" && runtimeMessage
            ? runtimeMessage
            : queries.length
              ? `${queries.length} OpenAlex quer${queries.length === 1 ? "y" : "ies"} issued`
              : "Graph held locally, no fresh literature pull",
        at: activeStepKey === "enrich" ? runtimeStageAt || agentAction?.created_at : agentAction?.created_at,
        status: stepStatus("enrich"),
      },
      {
        key: "alert",
        label: "Escalate",
        detail:
          activeStepKey === "alert" && runtimeMessage
            ? runtimeMessage
            : alertTitle || "No escalation beyond profile update",
        at: activeStepKey === "alert" ? runtimeStageAt || agentAction?.created_at : agentAction?.created_at,
        status: stepStatus("alert"),
      },
    ];

    return {
      currentStudent,
      currentStage: runtimeStage,
      runtimeMessage,
      noteAction,
      agentAction,
      cycleSummary,
      queries,
      newNodes,
      severity,
      trend,
      alertTitle,
      cycleNotes,
      processedStudents,
      steps,
    };
  }, [actions, activeProfile, data?.runtime, isRunning, notes.length, selectedStudent]);

  if (loading) {
    return (
      <main className="shell">
        <div className="aurora aurora-a" />
        <div className="aurora aurora-b" />
        <div className="grid-haze" />
        <section className="hero hero-idle">
          <div className="idle-card">
            <p className="eyebrow">Backend orchestration visualizer</p>
            <h1>Monty</h1>
            <p className="lede">Loading demo status and preparing the operator surface.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="grid-haze" />

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Backend orchestration visualizer</p>
          <h1>Monty</h1>
          <p className="lede">
            A live surface for the agentic loop: note ingestion, cumulative reassessment, targeted literature fetches, and escalating actions as the database changes in real time.
          </p>
        </div>
        <div className="hero-actions">
          <button className="primary" onClick={() => void startDemo(true)} disabled={bootstrapping}>
            {bootstrapping ? (isRunning ? "Restarting demo..." : "Starting demo...") : isRunning ? "Restart From Empty" : "Start Live Demo"}
          </button>
          <div className="runtime-pill">
            <span className="pulse" />
            <span>{isRunning ? "Live" : runtimeMode === "resetting" ? "Resetting" : "Ready"}</span>
            <span>{`notes ${data?.runtime.note_interval_seconds ?? 1}s`}</span>
            <span>{`agent ${data?.runtime.agent_interval_seconds ?? 2}s`}</span>
          </div>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="metrics">
        <Metric title="Notes Ingested" value={data?.counts.notes ?? 0} detail={`Latest ${timeLabel(notes[0]?.inserted_at)}`} />
        <Metric title="Profiles Live" value={data?.counts.profiles ?? 0} detail={`Focus ${activeProfile?.student_name || "pending"}`} />
        <Metric title="Knowledge Nodes" value={data?.counts.knowledge_nodes ?? 0} detail="OpenAlex-backed memory" />
        <Metric title="Open Alerts" value={data?.counts.alerts ?? 0} detail={`Latest ${alerts[0] ? relativeLabel(actions[0]?.created_at) : "none"}`} />
      </section>

      <section className="operations panel">
        <PanelHeader
          title="Live Workflow"
          subtitle="Structured as an operator surface: the step rail shows the current loop state, and the focus card shows exactly what the agent touched most recently."
        />
        {!isRunning ? (
          <div className="idle-card">
            <div>
              <span className="inspector-label">Ready state</span>
              <h2>Start from zero notes and watch the loop build live.</h2>
              <p>
                The visualizer is idle. Starting the demo will clear the current run state, begin note ingestion, and then show reassessment,
                knowledge enrichment, and escalation as they happen.
              </p>
            </div>
            <div className="idle-list">
              <div className="idle-list-item">
                <strong>1. Ingest</strong>
                <span>Insert a fresh classroom note.</span>
              </div>
              <div className="idle-list-item">
                <strong>2. Reassess</strong>
                <span>Rebuild the cumulative student profile.</span>
              </div>
              <div className="idle-list-item">
                <strong>3. Enrich</strong>
                <span>Fetch OpenAlex only when the graph is thin.</span>
              </div>
              <div className="idle-list-item">
                <strong>4. Escalate</strong>
                <span>Write alerts and recommended actions when needed.</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="operations-grid">
            <div className="step-rail">
              {liveSummary.steps.map((step, index) => (
                <article className={`step-card status-${step.status}`} key={step.key}>
                  <div className="step-index">{`0${index + 1}`}</div>
                  <div className="step-copy">
                    <strong>{step.label}</strong>
                    <p>{step.detail}</p>
                    <small>{step.at ? `${timeLabel(step.at)} · ${relativeLabel(step.at)}` : "pending"}</small>
                  </div>
                </article>
              ))}
            </div>

            <div className="focus-card">
              <div className="focus-topline">
                <span className={`severity-badge tone-${severityTone(liveSummary.severity)}`}>{liveSummary.severity}</span>
                <span>{liveSummary.currentStudent || "System active"}</span>
              </div>
              <h2>{liveSummary.currentStage ? titleCase(liveSummary.currentStage) : "Right now"}</h2>
              <p className="focus-text">
                {liveSummary.runtimeMessage
                  || (liveSummary.noteAction ? preview(String(liveSummary.noteAction.payload?.preview || ""), 190) : "Waiting for the next event.")}
              </p>
              <div className="focus-metrics">
                <div>
                  <span>Cycle scope</span>
                  <strong>{`${liveSummary.cycleNotes || 0} notes`}</strong>
                </div>
                <div>
                  <span>Students touched</span>
                  <strong>{liveSummary.processedStudents || 0}</strong>
                </div>
                <div>
                  <span>Knowledge delta</span>
                  <strong>{`+${liveSummary.newNodes}`}</strong>
                </div>
              </div>
              <div className="focus-queries">
                <span>Research activity</span>
                {liveSummary.queries.length ? (
                  liveSummary.queries.map((query) => (
                    <div className="query-pill" key={query}>
                      {query}
                    </div>
                  ))
                ) : (
                  <div className="query-pill subdued">No external fetch needed in the latest completed cycle</div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="content-grid">
        <div className="main-column">
          <div className="panel">
            <PanelHeader
              title="Knowledge Graph"
              subtitle="Nodes stay compact and labels stay off-canvas until you interact. Filter by student, inspect on click, and let the graph carry hierarchy instead of text clutter."
            />
            <KnowledgeGraph nodes={knowledgeNodes} selectedStudent={selectedStudent} />
          </div>

          <div className="panel">
            <PanelHeader
              title="Student Personality Graph"
              subtitle="The graph rebuilds from cumulative notes. Category nodes stay legible, while facet detail moves into an inspector instead of sitting on the canvas."
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
                    <span>{preview(activeProfile.latest_patterns, 96)}</span>
                  </div>
                </div>
                <PersonalityGraph studentName={activeProfile.student_name} facets={groupedFacets} />
              </>
            ) : (
              <div className="empty-state">Waiting for the first profile.</div>
            )}
          </div>
        </div>

        <div className="side-column">
          <CollapsiblePanel
            title="Note Ingestion"
            subtitle="Each card maps to a Ghost insertion. The newest note gets visual priority; older rows fall back."
            defaultOpen
            badge={`${notes.length} rows`}
          >
            <div className="note-stack">
              {notes.map((note, index) => (
                <article className="note-card" key={note.id} style={{ animationDelay: `${index * 65}ms` }}>
                  <div className="note-meta">
                    <span className="note-id">{`#${note.id}`}</span>
                    <span>{note.name}</span>
                    <span>{timeLabel(note.inserted_at)}</span>
                  </div>
                  <p>{preview(note.body)}</p>
                </article>
              ))}
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Agent Trace"
            subtitle="Raw execution log for ingestion, cycle summaries, and per-student agent actions."
            defaultOpen={false}
            badge={`${actions.length} events`}
          >
            <div className="trace-list">
              {actions.map((action) => (
                <article className="trace-item" key={action.id}>
                  <div className="trace-head">
                    <strong>{titleCase(action.action_kind)}</strong>
                    <span>{timeLabel(action.created_at)}</span>
                  </div>
                  <p className="trace-student">{action.student_name || "system"}</p>
                  <p>{preview(JSON.stringify(action.payload ?? {}, null, 0) || "", 190)}</p>
                </article>
              ))}
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Live Alerts"
            subtitle="Critical states stay pinned, but the queue can collapse when you want the graphs to take over."
            defaultOpen
            badge={`${alerts.length} open`}
          >
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
          </CollapsiblePanel>
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

function CollapsiblePanel({
  title,
  subtitle,
  badge,
  defaultOpen,
  children,
}: {
  title: string;
  subtitle: string;
  badge?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="panel collapsible" open={defaultOpen}>
      <summary className="collapsible-summary">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <div className="summary-actions">
          {badge ? <span className="summary-badge">{badge}</span> : null}
          <span className="chevron" aria-hidden="true" />
        </div>
      </summary>
      <div className="collapsible-content">{children}</div>
    </details>
  );
}

function KnowledgeGraph({
  nodes,
  selectedStudent,
}: {
  nodes: KnowledgeNode[];
  selectedStudent: string | null;
}) {
  const [filter, setFilter] = useState<string>("all");
  const [filterTouched, setFilterTouched] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const studentOptions = useMemo(() => {
    return Array.from(new Set(nodes.map((node) => node.student_name).filter(Boolean) as string[]));
  }, [nodes]);

  useEffect(() => {
    if (filterTouched) {
      if (filter !== "all" && !studentOptions.includes(filter)) {
        setFilter(studentOptions[0] || "all");
      }
      return;
    }
    if (selectedStudent && studentOptions.includes(selectedStudent)) {
      setFilter(selectedStudent);
    } else if (!studentOptions.length) {
      setFilter("all");
    }
  }, [filter, filterTouched, selectedStudent, studentOptions]);

  function chooseFilter(nextFilter: string) {
    setFilterTouched(true);
    setFilter(nextFilter);
  }

  const visibleNodes = useMemo(() => {
    const filtered = filter === "all" ? nodes : nodes.filter((node) => node.student_name === filter);
    return filtered.slice(0, filter === "all" ? 18 : 10);
  }, [filter, nodes]);

  useEffect(() => {
    if (!visibleNodes.some((node) => `paper-${node.id}` === selectedNodeId)) {
      setSelectedNodeId(visibleNodes[0] ? `paper-${visibleNodes[0].id}` : null);
    }
  }, [selectedNodeId, visibleNodes]);

  const nodesByStudent = useMemo(() => {
    return visibleNodes.reduce<Record<string, KnowledgeNode[]>>((acc, node) => {
      const key = node.student_name || "Shared";
      acc[key] = acc[key] || [];
      acc[key].push(node);
      return acc;
    }, {});
  }, [visibleNodes]);

  const studentNames = Object.keys(nodesByStudent);
  const selectedNode =
    visibleNodes.find((node) => `paper-${node.id}` === selectedNodeId) ||
    (studentNames.includes(selectedNodeId || "") ? null : visibleNodes[0]) ||
    null;

  return (
    <div className="graph-shell">
      <div className="graph-toolbar">
        <div className="chip-row">
          <button className={`filter-chip ${filter === "all" ? "selected" : ""}`} onClick={() => chooseFilter("all")}>
            All students
          </button>
          {studentOptions.map((student) => (
            <button
              className={`filter-chip ${filter === student ? "selected" : ""}`}
              key={student}
              onClick={() => chooseFilter(student)}
            >
              {student}
            </button>
          ))}
        </div>
        <small>{`${visibleNodes.length} visible papers · click a node for detail`}</small>
      </div>

      <svg viewBox="0 0 720 460" className="graph-svg" role="img" aria-label="Knowledge graph">
        <defs>
          <linearGradient id="knowledge-edge" x1="0%" x2="100%" y1="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(92, 226, 194, 0.9)" />
            <stop offset="100%" stopColor="rgba(255, 165, 84, 0.28)" />
          </linearGradient>
        </defs>
        <circle cx="360" cy="230" r="54" className="graph-core" />
        <text x="360" y="226" textAnchor="middle" className="graph-core-label">
          Monty
        </text>
        <text x="360" y="248" textAnchor="middle" className="graph-core-sub">
          research memory
        </text>

        {studentNames.map((student, studentIndex) => {
          const angle = (Math.PI * 2 * studentIndex) / Math.max(studentNames.length, 1) - Math.PI / 2;
          const studentX = 360 + Math.cos(angle) * 136;
          const studentY = 230 + Math.sin(angle) * 136;
          const cluster = nodesByStudent[student];
          const studentSelected = filter === student || selectedNode?.student_name === student;

          return (
            <g key={student} className={`graph-cluster ${studentSelected ? "focused" : ""}`}>
              <line x1="360" y1="230" x2={studentX} y2={studentY} className="graph-edge graph-edge-major" />
              <g onClick={() => chooseFilter(student)} role="button" tabIndex={0}>
                <circle cx={studentX} cy={studentY} r="18" className="graph-student-node" />
                <text x={studentX} y={studentY + 4} textAnchor="middle" className="graph-node-label small">
                  {student.split(" ")[0][0]}
                </text>
              </g>
              <text x={studentX} y={studentY - 28} textAnchor="middle" className="cluster-label">
                {student.split(" ")[0]}
              </text>

              {cluster.map((node, paperIndex) => {
                const orbitAngle = angle + (Math.PI * 2 * paperIndex) / Math.max(cluster.length, 1);
                const orbitRadius = 52 + (paperIndex % 2) * 12;
                const paperX = studentX + Math.cos(orbitAngle) * orbitRadius;
                const paperY = studentY + Math.sin(orbitAngle) * orbitRadius;
                const active = selectedNode?.id === node.id;
                const radius = 6 + Math.max(0, Math.min(6, (node.confidence || 0.4) * 6));
                return (
                  <g
                    key={node.id}
                    className={`paper-node ${active ? "active" : ""}`}
                    onClick={() => setSelectedNodeId(`paper-${node.id}`)}
                    role="button"
                    tabIndex={0}
                  >
                    <line x1={studentX} y1={studentY} x2={paperX} y2={paperY} className="graph-edge graph-edge-minor" />
                    <circle cx={paperX} cy={paperY} r={radius} className="graph-paper-node" />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      <div className="graph-inspector">
        <div>
          <span className="inspector-label">Selected research node</span>
          <h4>{selectedNode?.source_title || "Waiting for literature"}</h4>
          <p>{preview(selectedNode?.insights?.[0] || selectedNode?.topic || "The agent will populate this panel when new literature is added.", 210)}</p>
        </div>
        <div className="inspector-meta">
          <span>{selectedNode?.student_name || (filter === "all" ? "Shared memory" : filter)}</span>
          <span>{`${(selectedNode?.related_topics || []).length} related topics`}</span>
          {selectedNode?.source_url ? (
            <a href={selectedNode.source_url} target="_blank" rel="noreferrer">
              Open source
            </a>
          ) : null}
        </div>
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
    { key: "personality_trait", label: "Traits", x: 190, y: 70, values: facets.personality_trait },
    { key: "regulation_trigger", label: "Triggers", x: 530, y: 150, values: facets.regulation_trigger },
    { key: "support_strategy", label: "Supports", x: 455, y: 360, values: facets.support_strategy },
    { key: "behavioral_pattern", label: "Patterns", x: 170, y: 320, values: facets.behavioral_pattern },
  ] as const;

  const [activeGroupKey, setActiveGroupKey] = useState<string>(groups.find((group) => group.values.length)?.key || groups[0].key);
  const [activeFacetValue, setActiveFacetValue] = useState<string | null>(null);

  useEffect(() => {
    const nextGroup = groups.find((group) => group.values.length)?.key || groups[0].key;
    setActiveGroupKey(nextGroup);
    setActiveFacetValue(null);
  }, [studentName]);

  const activeGroup = groups.find((group) => group.key === activeGroupKey) || groups[0];
  const activeFacet =
    activeGroup.values.find((facet) => facet.facet_value === activeFacetValue) ||
    activeGroup.values[0] ||
    null;

  return (
    <div className="personality-layout">
      <svg viewBox="0 0 700 430" className="graph-svg personality-svg" role="img" aria-label="Personality graph">
        <circle cx="340" cy="215" r="58" className="person-core" />
        <text x="340" y="210" textAnchor="middle" className="graph-core-label">
          {studentName.split(" ")[0]}
        </text>
        <text x="340" y="234" textAnchor="middle" className="graph-core-sub">
          live profile state
        </text>

        {groups.map((group) => {
          const focused = group.key === activeGroup.key;
          return (
            <g
              key={group.key}
              className={`facet-group ${focused ? "focused" : ""}`}
              onClick={() => {
                setActiveGroupKey(group.key);
                setActiveFacetValue(group.values[0]?.facet_value || null);
              }}
              role="button"
              tabIndex={0}
            >
              <line x1="340" y1="215" x2={group.x} y2={group.y} className="person-edge" />
              <circle cx={group.x} cy={group.y} r="28" className="person-group" />
              <text x={group.x} y={group.y + 4} textAnchor="middle" className="graph-node-label small">
                {group.values.length}
              </text>
              <text x={group.x} y={group.y - 38} textAnchor="middle" className="cluster-label">
                {group.label}
              </text>

              {group.values.slice(0, 6).map((facet, index) => {
                const localAngle = (-Math.PI / 2) + (index * Math.PI) / Math.max(group.values.slice(0, 6).length - 1, 1);
                const dotRadius = 52 + (index % 2) * 10;
                const dotX = group.x + Math.cos(localAngle) * dotRadius;
                const dotY = group.y + Math.sin(localAngle) * dotRadius;
                const active = activeFacet?.facet_value === facet.facet_value;
                return (
                  <g
                    key={`${group.key}-${facet.facet_value}`}
                    className={`facet-node ${active ? "active" : ""}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      setActiveGroupKey(group.key);
                      setActiveFacetValue(facet.facet_value);
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <line x1={group.x} y1={group.y} x2={dotX} y2={dotY} className="person-edge faint" />
                    <circle cx={dotX} cy={dotY} r={6 + Math.round(facet.confidence * 4)} className="facet-dot" />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      <div className="personality-inspector">
        <div className="inspector-header">
          <span className="inspector-label">Selected facet cluster</span>
          <h4>{activeGroup.label}</h4>
        </div>
        {activeFacet ? (
          <>
            <div className="facet-chip">{activeFacet.facet_value}</div>
            <p>{preview(activeFacet.evidence, 240)}</p>
            <div className="confidence-row">
              <span>Confidence</span>
              <div className="confidence-bar">
                <span style={{ width: `${Math.round(activeFacet.confidence * 100)}%` }} />
              </div>
              <strong>{`${Math.round(activeFacet.confidence * 100)}%`}</strong>
            </div>
          </>
        ) : (
          <p>No facets available yet for this cluster.</p>
        )}
        <div className="facet-list">
          {activeGroup.values.map((facet) => (
            <button
              key={facet.facet_value}
              className={`facet-list-item ${activeFacet?.facet_value === facet.facet_value ? "selected" : ""}`}
              onClick={() => setActiveFacetValue(facet.facet_value)}
            >
              <span>{facet.facet_value}</span>
              <small>{`${Math.round(facet.confidence * 100)}%`}</small>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
