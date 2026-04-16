# Monty (PEP OS) — Project Guide

## What This Is

A hackathon project for the **Context Engineering Challenge**: build autonomous, self-improving AI agents that tap into real-time data sources, make sense of what they find, and take meaningful action without human intervention.

**Domain:** Montessori early childhood education. The system ingests teacher observation notes about toddlers/preschoolers, assesses behavioral patterns, finds relevant academic research, and surfaces actionable insights to educators.

## Team

- **Thilak** — Intelligence layer (FastAPI API + LLM assessment) and frontend (Next.js dashboard)
- **Indro** — Data layer (note generation, streaming, Ghost Build DB) and literature scraping (OpenAlex integration)

## Architecture (Big Picture)

```
notes_streamer/persona_engine.py (live LLM note generation)
  |
  v
notes_streamer/streamer.py --> Ghost DB1 (e3ho885uvg / test-db)
                                  table: ingested_observations
  |
  v
intelligence/api/agent_loop.py --> self_improve.py (LLM assessment)
  |                                --> wiki_writer.py (writes wiki/)
  v
wiki/ (markdown source of truth)
  behavioral/          <- anonymized behavioral KG nodes + edges
  students/<Name>/     <- per-student profile + incident pages
  sources/openalex/    <- research paper pages
  |
  v
wiki_indexer.py --> Ghost DB2 (oman6716dt / student-profiles)
                      tables: behavioral_nodes, behavioral_edges,
                              student_incidents, student_profiles_index
                              [+ legacy: profile_snapshots, student_profiles,
                                student_literature — being phased out in Phase 5b]
  |
  v
curiosity.py (curiosity gate) --> kg_agent.py (OpenAlex research)
  |                                --> wiki/sources/openalex/
  v
intelligence/api/main.py (FastAPI) --> backend_visualizer/ (Next.js live dashboard)
```

**wiki/ is the canonical source of truth.** Postgres tables are derived indexes rebuilt from disk by `wiki_indexer.full_rebuild()`. The persona engine generates synthetic teacher notes live via OpenAI (not from static files).

## Key Directories

| Directory | Owner | Purpose |
|-----------|-------|---------|
| `notes_streamer/` | Indro | Note parsing, streaming to Ghost DB |
| `notes_streamer/persona_engine.py` | Indro | Live LLM-driven synthetic note generator |
| `notes_streamer/literature_scraping/` | Indro | OpenAlex API client + paper retrieval |
| `intelligence/api/services/wiki_writer.py` | Shared | All writes to `wiki/`; enforces anonymization |
| `intelligence/api/services/wiki_indexer.py` | Shared | Syncs `wiki/` → Postgres index tables |
| `intelligence/api/services/curiosity.py` | Phase 3 | Curiosity gate — scores nodes, triggers research |
| `intelligence/api/services/kg_agent.py` | Phase 3 | Autonomous OpenAlex research agent |
| `intelligence/api/services/self_improve.py` | Shared | LLM assessment → wiki_writer integration |
| `intelligence/` | Thilak | FastAPI server, LLM services, agent loop |
| `backend_visualizer/` | Thilak | Next.js live visualizer dashboard |
| `wiki/` | Shared | Markdown source of truth (behavioral KG + student wikis) |
| `scripts/` | Shared | Maintenance scripts (migration, lint, verify) |
| `contracts/` | Shared | API keys (.env) |
| `notes/` | Indro | Static corpus (unused at runtime; persona engine is live) |

## Databases (Ghost Build / TimescaleDB)

| ID | Name | Tables |
|----|------|--------|
| `e3ho885uvg` | test-db | `ingested_observations` |
| `oman6716dt` | student-profiles | `behavioral_nodes`, `behavioral_edges`, `student_incidents`, `student_profiles_index`, `curiosity_events`, `agent_runtime_state` |
| `oman6716dt` | student-profiles | _(legacy, phasing out in Phase 5b)_ `student_profiles`, `profile_snapshots`, `student_literature`, `student_personality_graph`, `knowledge_graph` |

Connection strings are in `intelligence/api/services/ghost_client.py`.

> **Note:** The new index tables (`behavioral_nodes`, `behavioral_edges`, etc.) are derived from `wiki/` and can be rebuilt at any time with `python3 -m scripts.migrate_to_wiki` followed by `wiki_indexer.full_rebuild()`.

## API Endpoints (FastAPI on port 8000)

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/flags` | All students sorted by severity (red > yellow > green) |
| `GET /api/flags/{student_name}` | One student's full snapshot history |
| `GET /api/insights/{student_name}` | Summary, patterns, trend |
| `GET /api/suggestions/{student_name}` | Actionable recommendations |
| `GET /api/literature/{student_name}` | Research papers matched to student's behavioral profile |
| `GET /api/behavioral-graph` | Full behavioral KG (nodes + edges from wiki index) |
| `GET /api/student-graph/{name}` | One student's behavioral subgraph |
| `GET /api/personas` | List all personas (name, cadence, last note) |
| `PATCH /api/personas/{name}` | Update persona cadence or archetype |
| `POST /api/personas/{name}/inject` | Inject a manual note for a persona |
| `POST /api/personas/interact` | Free-form LLM interaction with a persona |
| `POST /api/persona/next-note` | Generate and stream next note from persona engine |
| `GET /api/curiosity/events` | Recent curiosity gate trigger events |
| `POST /api/curiosity/recompute/{slug}` | Re-score curiosity for a behavioral node |
| `POST /api/curiosity/investigate/{slug}` | Trigger immediate research investigation |
| `PATCH /api/runtime/curiosity-weights` | Adjust curiosity scoring weights at runtime |
| `GET /api/wiki/tree` | Directory listing of wiki/ |
| `GET /api/wiki/page` | Read a single wiki page (path param) |
| `POST /api/wiki/reindex` | Trigger full wiki→Postgres index rebuild |

## Running Things

```bash
# Start the API server
uvicorn intelligence.api.main:app --reload --port 8000

# Start the live visualizer dashboard
cd backend_visualizer && npm run dev

# Start the persona engine (generates notes live via OpenAI at configured cadence)
python -m notes_streamer.persona_engine

# Stream notes to Ghost DB (reads from persona engine output or legacy notes/)
python -m notes_streamer.streamer

# One-shot migration: legacy DB rows -> wiki/ markdown (dry-run first)
python3 -m scripts.migrate_to_wiki --dry-run
python3 -m scripts.migrate_to_wiki

# Lint behavioral wiki pages for anonymization leaks
python3 -m scripts.lint_anonymization

# Verify persona engine setup
python3 -m scripts.verify_persona_engine

# Legacy seed flows (kept for reference; use agent_loop + persona engine instead)
python -m intelligence.api.seed
python -m intelligence.api.seed_literature
```

## Environment Variables

Stored in `contracts/.env` and root `.env` (both gitignored):

- `OPENAI_API_KEY` — for GPT-4o-mini (note assessment + query generation)
- `OPENALEX_API_KEY` — for academic paper search

## Tech Stack

- **Backend:** Python, FastAPI, psycopg2, OpenAI SDK
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Database:** Ghost Build (managed TimescaleDB/PostgreSQL)
- **External APIs:** OpenAI (GPT-4o-mini), OpenAlex (scholarly papers)
- **Note format:** Plain text files with `Name: <student>\n\n<observation paragraphs>`

## Important Conventions

- DB connections use direct psycopg2 — no ORM; use `_conn(_agent_db_url())` (not `_connect_agent_db()`)
- Default cursor is `RealDictCursor` (rows are dicts, not tuples)
- `agent_runtime_state` keys on `key TEXT PRIMARY KEY`; override sentinel is `_god_mode`
- LLM calls return structured JSON via `response_format={"type": "json_object"}`
- Student names are the primary key for profiles (not UUIDs)
- **wiki/ is source of truth; Postgres is a derived index** — always write to wiki/ first, then index
- **Behavioral pages are anonymized; enforced by `anonymization_lint.py`** — no student names in `wiki/behavioral/`
- **Persona engine generates notes live via OpenAI** — `notes/` static corpus is unused at runtime
- OpenAlex searches are filtered to topics T10589, T13987, T14290 (early childhood education) and post-2010 papers
- Ghost Build CLI is used for DB management, psycopg2 for queries in code
- Do not touch `curiosity.py`, `kg_agent.py`, or `ghost_client.py` without coordination (Phase 3 / critical path)
