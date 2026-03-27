# Monty Backend Agent Plan

This plan is written against `Direction.txt` and the current repo state. It assumes the dashboard is not the demo priority and focuses on the backend loop: note ingestion, cumulative profile re-assessment, Ghost-backed graph state, knowledge enrichment, and emergency action.

## Pass 1: Rebalance the Input Stream

Objective:
Reduce the synthetic classroom to 5 repeat students so the agent can build visible longitudinal memory instead of shallow one-off snapshots.

Work:
- Regenerate `notes_streamer/notes` so every note belongs to exactly 1 of 5 students.
- Keep the corpus large enough to show pattern accumulation over time.
- Add 20 explicit emergency notes containing violent threats or self-harm language so the loop has obvious escalation cases.
- Change the streamer cadence to feel live for the demo: random note insertion every 10-50 seconds, without immediately repeating the same note selection.

Deliverables:
- `notes_streamer/notes`: 120 notes total, 5 students, 20 emergency cases.
- `scripts/generate_notes_corpus.py`: deterministic generator for the new corpus.
- `notes_streamer/streamer.py`: random-interval streaming with a shuffled note queue.

Validation:
- Confirm exactly 5 unique `Name:` headers.
- Confirm emergency files exist in the `problematic_101` to `problematic_120` range.
- Confirm streamer can run indefinitely without getting stuck in duplicate inserts too early.

## Pass 2: Add Persistent Agent Memory in Ghost

Objective:
Move the agent from transient script logic to durable state in Ghost so it can remember what it has seen, what it inferred, what research it found, and what actions it took.

Work:
- Keep `ingested_observations` as the note stream source of truth.
- Extend the agent-side Ghost schema with persistent runtime and graph tables:
  - `student_profiles`
  - `profile_snapshots`
  - `student_personality_graph`
  - `knowledge_graph`
  - `student_alerts`
  - `agent_actions`
  - `agent_runtime_state`
- Record the last processed note id so the loop only works on new observations unless a full rebuild is requested.
- Store both student-specific knowledge and shared KG query results in Ghost so the system improves over time instead of re-fetching from scratch.

Deliverables:
- `intelligence/api/services/ghost_client.py` with table creation, runtime checkpointing, graph persistence, alert persistence, and knowledge retrieval helpers.

Validation:
- A single setup call should create all required tables.
- Re-running the agent loop should be idempotent for the same note ids.
- Graph and alert rows should survive process restarts.

## Pass 3: Replace One-Shot Scoring with Cumulative Re-Assessment

Objective:
Implement the actual self-improving student loop described in `Direction.txt`: every cycle, the agent reassesses each impacted student using the full note history, not just the latest note.

Work:
- Keep per-note snapshot scoring for traceability.
- Add a second assessment path that looks at the full note history for each student and updates the aggregated profile.
- Extract durable personality facets from the accumulated notes:
  - classroom tendencies
  - triggers
  - support strategies
  - recurring behavioral patterns
- Use those facets to refresh the `student_personality_graph`.
- Add fallback heuristics so the backend still runs without an LLM key during the demo.

Deliverables:
- `intelligence/api/services/llm_service.py` with:
  - single-note assessment
  - full-history assessment
  - search query generation
  - research summarization
  - non-LLM fallback behavior
- `intelligence/api/services/self_improve.py` to orchestrate reassessment and profile updates.

Validation:
- When multiple notes arrive for the same student, `student_profiles` should reflect the full history, not just the last note.
- `student_personality_graph` should update on every affected student cycle.
- Severity should escalate to `red` for emergency language even if earlier notes were benign.

## Pass 4: Build the Knowledge Enrichment Loop

Objective:
Make the system visibly agentic by comparing profiles against what it already knows, detecting gaps, and only then querying OpenAlex to expand the Ghost-backed knowledge graph.

Work:
- Search the local `knowledge_graph` first using the latest profile context.
- Define “not enough useful knowledge” pragmatically as too few relevant KG matches or an emergency case that needs more targeted support.
- When knowledge is thin, generate targeted research queries and search OpenAlex.
- Persist:
  - literature rows in `student_literature`
  - KG nodes in `knowledge_graph`
  - the extracted research insights and related topics
- Expose on-demand KG lookup through:
  - `POST /api/kg-agent/query` on port 5001
  - `POST /api/kg/query` in the main API

Deliverables:
- `intelligence/api/services/kg_agent.py`
- `agents/server.py`
- Main API proxy endpoint for KG lookup

Validation:
- A student with no matching KG nodes should trigger research fetches.
- Repeated KG queries should return existing Ghost-backed knowledge before doing more research.
- The KG server should answer the contract-shaped request and response from the spec.

## Pass 5: Operationalize the Loop for the Demo

Objective:
Turn the backend into a live demo flow that matches the direction document without depending on the dashboard.

Work:
- Add an agent loop runner that executes every 30 seconds.
- On each cycle:
  1. read new notes from Ghost
  2. update affected student profiles
  3. compare profiles to knowledge graph state
  4. enrich knowledge when needed
  5. populate or update alerts
- For emergency notes, immediately:
  - create a critical alert
  - log an emergency agent action
  - print recommended actions and research-backed suggestions to the console
- Add inspection endpoints so the backend can be demoed directly:
  - `/api/agent/status`
  - `/api/alerts`
  - `/api/personality-graph/{student_name}`
  - `/api/knowledge-graph/{student_name}`

Deliverables:
- `intelligence/api/agent_loop.py`
- `intelligence/api/main.py` API surface for status, alerts, personality graph, KG, and manual cycle triggering

Validation:
- With the streamer running, a new note should eventually produce updated profile state and alerts without manual reseeding.
- Emergency notes should show console output immediately in the next agent cycle.
- The backend demo should be explainable as a five-step loop using only terminal output and HTTP responses.
