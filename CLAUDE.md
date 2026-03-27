# Monty (PEP OS) — Project Guide

## What This Is

A hackathon project for the **Context Engineering Challenge**: build autonomous, self-improving AI agents that tap into real-time data sources, make sense of what they find, and take meaningful action without human intervention.

**Domain:** Montessori early childhood education. The system ingests teacher observation notes about toddlers/preschoolers, assesses behavioral patterns, finds relevant academic research, and surfaces actionable insights to educators.

## Team

- **Thilak** — Intelligence layer (FastAPI API + LLM assessment) and frontend (Next.js dashboard)
- **Indro** — Data layer (note generation, streaming, Ghost Build DB) and literature scraping (OpenAlex integration)

## Architecture

```
Teacher Notes (.txt files in notes/)
  |
  v
notes_streamer/streamer.py --> Ghost DB1 (e3ho885uvg / test-db)
                                  table: ingested_observations (id, name, body)
  |
  v
intelligence/api/seed.py --> LLM (GPT-4o-mini) assesses each note
  |
  v
Ghost DB2 (oman6716dt / student-profiles)
  tables: profile_snapshots, student_profiles
  |
  v
intelligence/api/seed_literature.py --> LLM generates search queries from aggregated profiles
  |                                      --> OpenAlex API (filtered to early childhood education topics)
  v
Ghost DB2: student_literature table
  |
  v
intelligence/api/main.py (FastAPI) --> frontend/ (Next.js dashboard)
```

## Key Directories

| Directory | Owner | Purpose |
|-----------|-------|---------|
| `notes_streamer/` | Indro | Note parsing, streaming to Ghost DB, OpenAlex client |
| `notes_streamer/literature_scraping/` | Indro | OpenAlex API client + paper retrieval |
| `intelligence/` | Thilak | FastAPI server, LLM services, seed scripts |
| `frontend/` | Thilak | Next.js dashboard |
| `contracts/` | Shared | API keys (.env) |
| `notes/` | Indro | 100 synthetic teacher observation notes |

## Databases (Ghost Build / TimescaleDB)

| ID | Name | Tables |
|----|------|--------|
| `e3ho885uvg` | test-db | `ingested_observations` |
| `oman6716dt` | student-profiles | `student_profiles`, `profile_snapshots`, `student_literature` |

Connection strings are in `intelligence/api/services/ghost_client.py`.

## API Endpoints (FastAPI on port 8000)

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/flags` | All students sorted by severity (red > yellow > green) |
| `GET /api/flags/{student_name}` | One student's full snapshot history |
| `GET /api/insights/{student_name}` | Summary, patterns, trend |
| `GET /api/suggestions/{student_name}` | Actionable recommendations |
| `GET /api/literature/{student_name}` | Research papers matched to student's behavioral profile |

## Running Things

```bash
# Start the API server
uvicorn intelligence.api.main:app --reload --port 8000

# Seed behavioral assessments (reads all notes, runs LLM on each)
python -m intelligence.api.seed

# Seed literature (reads profiles, generates queries, searches OpenAlex)
python -m intelligence.api.seed_literature

# Start the frontend
cd frontend && npm run dev

# Stream notes to Ghost DB
python -m notes_streamer.streamer
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

- DB connections use direct psycopg2 — no ORM
- LLM calls return structured JSON via `response_format={"type": "json_object"}`
- Student names are the primary key for profiles (not UUIDs)
- The `notes/` directory has 50 neutral + 50 problematic observation notes
- OpenAlex searches are filtered to topics T10589, T13987, T14290 (early childhood education) and post-2010 papers
- Ghost Build CLI is used for DB management, psycopg2 for queries in code
