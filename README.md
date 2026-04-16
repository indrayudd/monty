# Monty (PEP OS)

Autonomous AI agent system for Montessori early childhood education. Ingests teacher observation notes, maintains a markdown-first behavioral knowledge graph, surfaces research-backed insights to educators, and continuously self-improves through a curiosity-driven research loop.

Built for the **Context Engineering Challenge**.

---

## Current State

The system is fully live end-to-end:

- **Persona engine** generates synthetic teacher observation notes in real time via GPT-4o-mini, simulating distinct student personas with configurable behavioral archetypes and note cadences.
- **Streamer** ingests notes into Ghost Build (TimescaleDB), triggering the agent loop.
- **Agent loop + self_improve** runs LLM assessment on each note and writes structured findings to the **wiki/** markdown store.
- **wiki/** is the canonical source of truth — a markdown knowledge graph of anonymized behavioral patterns, per-student incident pages, and sourced research papers.
- **Curiosity gate** continuously scores behavioral nodes for novelty and triggers autonomous OpenAlex research investigations when curiosity exceeds threshold.
- **Postgres index tables** (`behavioral_nodes`, `behavioral_edges`, `student_incidents`) are derived from wiki/ and rebuilt on demand.
- **Live visualizer dashboard** (Next.js, port 3001) shows the behavioral graph, student timelines, persona controls, and the God Mode story preset panel in real time.

---

## Architecture

```
notes_streamer/persona_engine.py
  (live GPT-4o-mini note generation per persona)
  |
  v
notes_streamer/streamer.py
  --> Ghost DB1 (e3ho885uvg / test-db)
        table: ingested_observations
  |
  v
intelligence/api/agent_loop.py
  --> services/self_improve.py (LLM behavioral assessment)
  --> services/wiki_writer.py  (writes wiki/ markdown)
  |
  v
wiki/                          <-- source of truth
  behavioral/                  <- anonymized KG nodes + edges
    setting_events/, antecedents/, behaviors/,
    functions/, brain_states/, responses/, protective_factors/
    _edges/
  students/<Name>/             <- per-student profile + incident pages
    profile.md
    incidents/YYYY-MM-DD-HHMM-<slug>.md
  sources/openalex/            <- research paper pages
  personas/                    <- immutable persona definitions
  log.md                       <- agent action log
  |
  v
services/wiki_indexer.py
  --> Ghost DB2 (oman6716dt / student-profiles)
        behavioral_nodes, behavioral_edges,
        student_incidents, student_profiles_index
  |
  v
services/curiosity.py (curiosity gate)
  scores behavioral nodes for novelty/urgency
  --> services/kg_agent.py (autonomous research agent)
        --> OpenAlex API
        --> wiki/sources/openalex/<id>.md
  |
  v
intelligence/api/main.py (FastAPI, port 8000)
  |
  v
backend_visualizer/ (Next.js, port 3001)
  Behavioral graph, student timelines, persona controls, God Mode panel
```

---

## Main Components

| Path | Purpose |
|------|---------|
| `notes_streamer/persona_engine.py` | Live LLM note generator; configurable archetypes and cadence per student persona |
| `notes_streamer/streamer.py` | Polls persona engine, streams notes to Ghost DB1 |
| `intelligence/api/agent_loop.py` | Orchestrates self_improve → wiki_writer cycle |
| `intelligence/api/services/self_improve.py` | LLM note assessment; writes behavioral nodes, edges, and student incidents via wiki_writer |
| `intelligence/api/services/wiki_writer.py` | Single write gateway for wiki/; enforces anonymization on behavioral pages |
| `intelligence/api/services/wiki_indexer.py` | Syncs wiki/ → Postgres index tables; `full_rebuild()` replays from disk |
| `intelligence/api/services/wiki_paths.py` | Path conventions and slugification for wiki/; no other service should hand-build wiki paths |
| `intelligence/api/services/curiosity.py` | Curiosity gate: scores behavioral nodes, emits `curiosity_events` rows |
| `intelligence/api/services/kg_agent.py` | Autonomous research agent; queries OpenAlex and writes sources to wiki/ |
| `intelligence/api/services/ghost_client.py` | All DB helpers; uses `_conn(_agent_db_url())` + `RealDictCursor` |
| `intelligence/api/services/anonymization_lint.py` | Asserts no student names appear in wiki/behavioral/ pages |
| `intelligence/api/services/llm_service.py` | OpenAI client wrapper (GPT-4o-mini, structured JSON output) |
| `intelligence/api/main.py` | FastAPI application; all API routes |
| `backend_visualizer/` | Next.js live dashboard (behavioral graph, console, wiki browser, God Mode) |
| `scripts/migrate_to_wiki.py` | One-shot migration of legacy DB rows into wiki/ markdown |
| `scripts/lint_anonymization.py` | CLI wrapper for anonymization_lint; exit non-zero on violation |
| `wiki/` | Markdown source of truth for entire knowledge graph |

---

## API Endpoints (FastAPI, port 8000)

### Student flags and profiles
| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/flags` | All students sorted by severity (red > yellow > green) |
| `GET /api/flags/{student_name}` | One student's full snapshot history |
| `GET /api/insights/{student_name}` | Summary, patterns, trend |
| `GET /api/suggestions/{student_name}` | Actionable recommendations |
| `GET /api/literature/{student_name}` | Research papers matched to student's behavioral profile |

### Behavioral knowledge graph
| Endpoint | Description |
|----------|-------------|
| `GET /api/behavioral-graph` | Full behavioral KG (nodes + edges from Postgres index) |
| `GET /api/student-graph/{name}` | One student's behavioral subgraph |
| `GET /api/student-graph/{name}/research` | Research papers linked to student's behavioral nodes |

### Persona engine
| Endpoint | Description |
|----------|-------------|
| `GET /api/personas` | List all personas with cadence and last-note metadata |
| `PATCH /api/personas/{name}` | Update persona cadence or behavioral archetype |
| `POST /api/personas/{name}/inject` | Inject a manual observation note for a persona |
| `POST /api/personas/interact` | Free-form LLM interaction with a persona |
| `POST /api/persona/next-note` | Generate and ingest the next note from the persona engine |

### Curiosity gate
| Endpoint | Description |
|----------|-------------|
| `GET /api/curiosity/events` | Recent curiosity gate trigger events |
| `POST /api/curiosity/recompute/{slug}` | Re-score curiosity for a behavioral node |
| `POST /api/curiosity/investigate/{slug}` | Trigger immediate research investigation for a node |
| `PATCH /api/runtime/curiosity-weights` | Adjust curiosity scoring weights at runtime |

### Wiki
| Endpoint | Description |
|----------|-------------|
| `GET /api/wiki/tree` | Directory listing of wiki/ |
| `GET /api/wiki/page` | Read a single wiki page (query param: `path`) |
| `POST /api/wiki/reindex` | Trigger full wiki→Postgres index rebuild |

### Agent / demo
| Endpoint | Description |
|----------|-------------|
| `GET /api/agent/status` | Agent loop runtime state |
| `POST /api/agent/run-cycle` | Trigger one agent loop cycle |
| `POST /api/demo/bootstrap` | Bootstrap demo data |
| `POST /api/demo/start` | Start automated demo loop |
| `POST /api/demo/reset` | Reset demo state |
| `POST /api/demo/stop` | Stop demo loop |
| `GET /api/demo/overview` | Full demo runtime overview |

---

## How to Run

### Prerequisites

- Python 3.12+, Node.js 18+
- Ghost Build credentials (TimescaleDB) in `contracts/.env` or root `.env`
- `OPENAI_API_KEY` for note assessment + persona engine
- `OPENALEX_API_KEY` for research paper search

### Start the system

```bash
# 1. Start the FastAPI backend
uvicorn intelligence.api.main:app --reload --port 8000

# 2. Start the live visualizer dashboard
cd backend_visualizer && npm run dev
# Dashboard at http://localhost:3001

# 3. Start the persona engine (live note generation via OpenAI)
python -m notes_streamer.persona_engine
# Generates notes at configured cadence per persona; feeds the streamer

# 4. Start the streamer (ingests persona engine output to Ghost DB)
python -m notes_streamer.streamer
```

### Maintenance

```bash
# Migrate legacy DB rows to wiki/ (idempotent; dry-run first)
python3 -m scripts.migrate_to_wiki --dry-run
python3 -m scripts.migrate_to_wiki

# Lint behavioral wiki pages for anonymization leaks
python3 -m scripts.lint_anonymization

# Verify persona engine setup
python3 -m scripts.verify_persona_engine

# Rebuild Postgres index tables from wiki/ (via API)
curl -X POST http://localhost:8000/api/wiki/reindex
```

---

## Recommended Demo Flow

1. **Start all services** (backend + visualizer + persona engine + streamer).
2. Open the visualizer at `http://localhost:3001`.
3. Navigate to the **Behavioral Graph** panel — watch nodes and edges appear as the agent loop processes notes.
4. Navigate to the **Console** panel — see curiosity events fire and research investigations trigger automatically.
5. Navigate to the **Wiki Browser** panel — browse `wiki/behavioral/` nodes and `wiki/students/<Name>/incidents/` pages written in real time.
6. **God Mode story presets** (Visualizer → God Mode panel): select a preset scenario (e.g., "Escalating Aggression") to inject a curated note sequence across personas, watch the behavioral graph respond, and see curiosity gate trigger targeted OpenAlex research.
7. Use `PATCH /api/personas/{name}` or the Personas panel to tweak archetypes and cadences mid-demo.

---

## Environment Variables

Stored in `contracts/.env` and root `.env` (both gitignored):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | GPT-4o-mini — note assessment, persona engine, curiosity queries |
| `OPENALEX_API_KEY` | OpenAlex scholarly paper search |
| Ghost Build connection strings | Set in `intelligence/api/services/ghost_client.py` |

---

## Databases

| Ghost Build ID | Name | Purpose |
|----------------|------|---------|
| `e3ho885uvg` | test-db | `ingested_observations` — raw note stream |
| `oman6716dt` | student-profiles | Behavioral KG index + student incident index + curiosity events |

New index tables (derived from wiki/, rebuiltable): `behavioral_nodes`, `behavioral_edges`, `student_incidents`, `student_profiles_index`, `curiosity_events`, `agent_runtime_state`.

Legacy tables (being phased out in Phase 5b): `student_profiles`, `profile_snapshots`, `student_literature`, `student_personality_graph`, `knowledge_graph`.

---

## Tech Stack

- **Backend:** Python, FastAPI, psycopg2, OpenAI SDK
- **Frontend/Visualizer:** Next.js, TypeScript, Tailwind CSS
- **Database:** Ghost Build (managed TimescaleDB/PostgreSQL)
- **External APIs:** OpenAI (GPT-4o-mini), OpenAlex (scholarly papers)
- **Wiki format:** Python-frontmatter markdown files with YAML front matter
