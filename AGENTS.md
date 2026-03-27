# Monty (PEP OS) — Agent Onboarding

## Hackathon Goal

**Context Engineering Challenge:** Build autonomous, self-improving AI agents that tap into real-time data sources, make sense of what they find, and take meaningful action without human intervention.

We're building a system for Montessori educators that: ingests teacher observation notes about toddlers -> assesses behavior via LLM -> finds relevant academic research -> surfaces insights and suggestions through a dashboard.

## Current Progress (as of 2026-03-27)

### DONE

- [x] **100 synthetic teacher observation notes** in `notes/` (50 neutral, 50 problematic)
- [x] **Note parser + streamer** — parses .txt notes, streams them to Ghost DB1
- [x] **Ghost DB1** (test-db) populated with `ingested_observations` table
- [x] **Behavioral assessment pipeline** (`intelligence/api/seed.py`) — reads all notes, calls GPT-4o-mini, stores per-note assessments in `profile_snapshots` and aggregated `student_profiles` in Ghost DB2
- [x] **20 student profiles** seeded with severity (red/yellow/green), behavioral patterns, trend tracking
- [x] **OpenAlex API client** — searches scholarly papers, downloads metadata, scores/ranks results
- [x] **Literature pipeline** (`intelligence/api/seed_literature.py`) — reads aggregated student profiles, LLM generates targeted search queries, fetches papers from OpenAlex filtered to early childhood education topics (T10589, T13987, T14290), stores in `student_literature` table
- [x] **FastAPI intelligence API** with 6 endpoints: health, flags, flags/{name}, insights/{name}, suggestions/{name}, literature/{name}
- [x] **Next.js frontend** with dashboard page, student detail page, components for flags/interpretations/suggestions/stats/student table

### NOT DONE — What Remains

- [ ] **Frontend: literature panel** — The `/api/literature/{student_name}` endpoint exists but the frontend doesn't display it yet. Add a section on the student detail page (`frontend/app/student/[name]/page.tsx`) showing matched research papers with titles, authors, abstracts, and links.
- [ ] **Frontend: polish and design** — Current UI is functional but needs visual polish for the demo. Make it look alive and adaptive per the hackathon judging criteria.
- [ ] **Self-improvement loop (CRITICAL for judging)** — The system currently does one-shot assessment. It needs a visible self-improvement mechanism:
  - Option A: Prompt versioning — track prompt performance, auto-refine prompts when quality drops
  - Option B: KG enrichment loop — when the LLM identifies knowledge gaps, auto-trigger more OpenAlex searches
  - Option C: Re-assessment — when new notes arrive for a student, re-evaluate their profile incorporating all historical notes, not just the latest
  - The spec mentions `services/self_improve.py` but it doesn't exist yet
- [ ] **KG Agent trigger endpoint** — Spec calls for `POST /api/kg-agent/query` on port 5001 (Indro's responsibility) and a proxy at `/api/kg/query` in the intelligence API. Neither exists yet.
- [ ] **End-to-end live demo flow** — Currently seed scripts run manually. For the demo, ideally show: new note arrives -> auto-assessed -> literature fetched -> dashboard updates live
- [ ] **Push blocked by GitHub secret scanning** — The OpenAI API key in `contracts/.env` is in git history. Repo owner needs to unblock via GitHub security settings, or the key needs to be removed from history.

## File Map

```
monty/
├── CLAUDE.md                    # Project guide (you're reading the companion)
├── AGENTS.md                    # This file
├── .env                         # OPENALEX_API_KEY (gitignored)
├── contracts/.env               # OPENAI_API_KEY (gitignored, but leaked in git history)
├── notes/                       # 100 .txt observation notes (neutral_001..050, problematic_051..100)
├── notes_streamer/
│   ├── note_parser.py           # Parses Name + body from .txt files
│   ├── streamer.py              # Streams random notes to Ghost DB1
│   ├── ghost_build.py           # Ghost Build CLI wrapper + SQL via subprocess
│   └── literature_scraping/
│       ├── api_usage_example.py      # OpenAlexClient, scoring, metadata extraction
│       └── toddler_literature_trace.py  # OLD per-note literature search (superseded by seed_literature.py)
├── intelligence/
│   ├── api/
│   │   ├── main.py              # FastAPI app — 6 endpoints
│   │   ├── seed.py              # Seed behavioral assessments (notes -> LLM -> DB2)
│   │   ├── seed_literature.py   # Seed literature (profiles -> LLM queries -> OpenAlex -> DB2)
│   │   └── services/
│   │       ├── ghost_client.py  # DB1/DB2 connections, all SQL queries
│   │       └── llm_service.py   # GPT-4o-mini calls: assess_note(), generate_search_queries()
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Dashboard home — student list with severity
│   │   ├── student/[name]/page.tsx  # Student detail page
│   │   ├── lib/api.ts           # Fetch wrapper for intelligence API
│   │   └── components/          # FlagAlerts, Interpretations, Suggestions, StatsCards, StudentSelector, StudentsTable
│   ├── CLAUDE.md / AGENTS.md    # Frontend-specific agent guides
├── spec_integration.md          # Shared contract between Thilak and Indro
├── spec_thilak.md               # Thilak's scope spec
├── spec_indro.md                # Indro's scope spec
└── openalex_agents.md           # OpenAlex API reference
```

## Database Schema

### Ghost DB1: `e3ho885uvg` (test-db)

```sql
ingested_observations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    UNIQUE (name, body)
)
```

### Ghost DB2: `oman6716dt` (student-profiles)

```sql
student_profiles (
    student_name TEXT PRIMARY KEY,
    current_severity TEXT,        -- green/yellow/red
    previous_severity TEXT,
    trend TEXT,                   -- improving/declining/stable
    assessment_count INT,
    latest_summary TEXT,
    latest_patterns TEXT,
    latest_suggestions TEXT,
    first_assessed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

profile_snapshots (
    id BIGSERIAL PRIMARY KEY,
    student_name TEXT,
    note_id INT,
    severity TEXT,
    profile_summary TEXT,
    behavioral_patterns TEXT,
    suggestions TEXT,
    snapshot_at TIMESTAMPTZ,
    UNIQUE (student_name, note_id)
)

student_literature (
    id BIGSERIAL PRIMARY KEY,
    student_name TEXT NOT NULL,
    search_query TEXT NOT NULL,
    openalex_id TEXT NOT NULL,
    title TEXT,
    authors TEXT,
    publication_year INT,
    cited_by_count INT DEFAULT 0,
    abstract TEXT,
    landing_page_url TEXT,
    relevance_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (student_name, openalex_id)
)
```

## How to Run

```bash
# Backend API
uvicorn intelligence.api.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Re-seed if needed (destructive — truncate tables first)
python -m intelligence.api.seed
python -m intelligence.api.seed_literature
```

## Key Design Decisions

1. **Aggregated profiles drive literature search, not individual notes** — One note is too granular. We aggregate all notes per student into behavioral patterns, then search for papers matching the pattern.
2. **OpenAlex filtered to early childhood education topics** — Topics T10589, T13987, T14290, post-2010, open access only. Prevents off-topic results (COVID papers, obesity studies).
3. **LLM prompt is tightly constrained** for search queries — must include "toddler/preschool" + "Montessori/early childhood classroom" + specific behavioral terms.
4. **Student name is the primary key**, not UUID. Keeps things simple for the hackathon.
5. **No ORM** — Direct psycopg2 with raw SQL. Connection strings are hardcoded in `ghost_client.py`.
