# Decoupled KGs + LLM-Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Monty's mixed-purpose `knowledge_graph` table with two decoupled markdown-first knowledge graphs (anonymized cross-student behavioral KG + per-student wikis), introduce a quantifiable curiosity gate that drives autonomous research, replace the static-corpus note generator with a live persona-driven LLM engine, and rebuild the backend visualizer with stacked linked panels + Wiki Browser + God Mode slide-in panel.

**Architecture:** Markdown source-of-truth under `wiki/`, Postgres as a derived index updated synchronously by a wiki-writer service. ABC + SEAT + BrainState behavioral taxonomy. 6-signal curiosity score gates research per node with cooldown. Persona engine generates notes live conditioned on per-persona slider state + cross-student context.

**Tech Stack:** Python 3.11+ (FastAPI, psycopg2, OpenAI SDK, `python-frontmatter`), Next.js 15 + TypeScript + Tailwind (`react-force-graph-2d` for KG canvas, `react-markdown` + `remark-wiki-link` for the wiki browser), Ghost Build TimescaleDB/Postgres.

---

## Spec reference

This plan implements the design in `docs/superpowers/specs/2026-04-16-decoupled-kgs-and-llm-wiki-design.md`. Read that first. The vision/UI brief is `VISION.md`. The llm-wiki paradigm origin is `llm-wiki.md`.

---

## File structure

### New backend files
- `intelligence/api/services/wiki_paths.py` — path conventions, slugification, frontmatter helpers
- `intelligence/api/services/anonymization_lint.py` — scan behavioral writes for PII
- `intelligence/api/services/wiki_writer.py` — write/update markdown for nodes, edges, incidents, rollups
- `intelligence/api/services/wiki_indexer.py` — sync markdown → Postgres index tables
- `intelligence/api/services/curiosity.py` — 6-signal score, gate evaluation, cooldown
- `notes_streamer/persona_engine.py` — LLM-driven note generator
- `scripts/migrate_to_wiki.py` — one-shot migration of legacy DB rows
- `scripts/verify_wiki_writer.py`, `scripts/verify_curiosity.py`, `scripts/verify_persona_engine.py`, `scripts/verify_anonymization.py` — behavior validation scripts
- `scripts/lint_anonymization.py` — CLI lint for `wiki/behavioral/**`

### Modified backend files
- `intelligence/api/services/ghost_client.py` — drop legacy graph helpers, add new index table CRUD, `god_mode_overrides` column
- `intelligence/api/services/self_improve.py` — emit incident pages via `wiki_writer` instead of writing legacy tables
- `intelligence/api/services/kg_agent.py` — call curiosity gate, write paper pages to `wiki/sources/openalex/`, link from student literature
- `intelligence/api/main.py` — add new endpoints, replace deprecated ones
- `notes_streamer/streamer.py` — pull from persona engine; remove static-corpus path
- `intelligence/requirements.txt` — add `python-frontmatter`

### New wiki content
- `wiki/schema.md`, `wiki/index.md`, `wiki/log.md`
- `wiki/behavioral/{setting_events,antecedents,behaviors,functions,brain_states,responses,protective_factors,_edges}/.gitkeep`
- `wiki/behavioral/_index.md`
- `wiki/students/{Arjun_Nair,Diya_Malhotra,Kiaan_Gupta,Mira_Shah,Saanvi_Verma}/.gitkeep`
- `wiki/personas/Arjun_Nair.md`, `Diya_Malhotra.md`, `Kiaan_Gupta.md`, `Mira_Shah.md`, `Saanvi_Verma.md` (hand-authored)
- `wiki/sources/openalex/.gitkeep`

### New frontend files (`backend_visualizer/app/`)
- `components/BehavioralKGPanel.tsx`, `StageRail.tsx`, `StudentTimeline.tsx`, `IncidentDrawer.tsx`
- `components/GodModePanel.tsx`, `PersonaCard.tsx`, `StoryPresetRow.tsx`, `CuriosityTuning.tsx`, `ManualResearchTrigger.tsx`
- `components/WikiFileTree.tsx`, `WikiPageRenderer.tsx`, `WikiBacklinks.tsx`
- `components/CuriosityEventsStream.tsx`, `TopAppBar.tsx`
- `wiki/page.tsx`, `console/page.tsx`
- `lib/api.ts` (extend), `lib/wikilink.ts` (new)

### Removed files
- `scripts/generate_notes_corpus.py` (Phase 5)
- `notes_streamer/notes/*.txt` (kept in git history; no longer used at runtime)

---

## Validation convention (no test framework)

Per `CLAUDE.md`, this repo has no pytest / jest setup. Validation in this plan uses:

1. **Syntax**: `python3 -m py_compile <files>` after every Python edit.
2. **Behavior**: `scripts/verify_<feature>.py` — small scripts using stdlib `assert`; run as `python3 -m scripts.verify_X`; exit non-zero on failure.
3. **Endpoint**: `curl -s <url> | jq <expr>` returning expected JSON shape; pipe through `test` if needed.
4. **Frontend build**: `cd backend_visualizer && npm run build`.
5. **Lint**: `python3 -m scripts.lint_anonymization` — walks `wiki/behavioral/` for PII.
6. **Manual demo**: where the validation is a UI behavior, the task lists explicit click-through steps.

Do **not** introduce pytest, jest, vitest, or any test framework — it would be inconsistent with the project's chosen approach.

---

## Parallelism map (for subagent dispatch)

```
Phase 0 (sequential prerequisite — single agent)
   │
   ├──► Phase 1 (persona engine)        ─┐
   │                                     │
   ├──► Phase 2 (wiki writer + indexer) ─┤
   │           │                         │  All four can run in parallel after Phase 0
   │           └──► Phase 3 (curiosity)  │  (curiosity depends on Phase 2 wiki writer)
   │                                     │
   └──► Phase 4 (visualizer)             ─┘  Develops against Phase 0 stub endpoints
                                              Polishes after Phases 1-3 ship real data
   │
   └──► Phase 5 (migration + docs)       ─── Sequential, after all above complete
```

Phases 1, 2, and 4 share **no files** with each other. Phase 3 modifies `kg_agent.py` and depends on `wiki_writer` from Phase 2.

---

## Commit conventions

- One task = one commit minimum (more commits inside a task are fine).
- Commit messages: `phase<N>: <imperative summary>`. Example: `phase2: add wiki_writer for behavioral nodes`.
- Co-author trailer: `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`.
- Don't sweep unrelated staged files into a commit. Always commit by explicit path.

---

## Phase 0 — Scaffolding (sequential prerequisite)

Goal: every downstream phase can compile and run against stubbed dependencies. Existing demo continues to work unchanged.

### Task 0.1: Add `python-frontmatter` dependency

**Files:**
- Modify: `intelligence/requirements.txt`

- [ ] **Step 1: Add dependency line**

Append to `intelligence/requirements.txt`:
```
python-frontmatter==1.1.0
```

- [ ] **Step 2: Install locally**

Run: `pip install -r intelligence/requirements.txt`
Expected: installs `python-frontmatter` and its `PyYAML` dep without errors.

- [ ] **Step 3: Smoke import**

Run: `python3 -c "import frontmatter; print(frontmatter.__version__)"`
Expected: prints `1.1.0`.

- [ ] **Step 4: Commit**

```bash
git add intelligence/requirements.txt
git commit -m "phase0: add python-frontmatter dependency

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.2: Create wiki/ skeleton

**Files:**
- Create: `wiki/schema.md`, `wiki/index.md`, `wiki/log.md`
- Create: `wiki/behavioral/{setting_events,antecedents,behaviors,functions,brain_states,responses,protective_factors,_edges}/.gitkeep`
- Create: `wiki/behavioral/_index.md`
- Create: `wiki/students/{Arjun_Nair,Diya_Malhotra,Kiaan_Gupta,Mira_Shah,Saanvi_Verma}/.gitkeep`
- Create: `wiki/sources/openalex/.gitkeep`
- Create: `wiki/personas/.gitkeep` (personas authored in Task 0.3)

- [ ] **Step 1: Create directory structure**

Run:
```bash
mkdir -p wiki/behavioral/{setting_events,antecedents,behaviors,functions,brain_states,responses,protective_factors,_edges}
mkdir -p wiki/students/{Arjun_Nair,Diya_Malhotra,Kiaan_Gupta,Mira_Shah,Saanvi_Verma}
mkdir -p wiki/sources/openalex
mkdir -p wiki/personas
touch wiki/behavioral/setting_events/.gitkeep wiki/behavioral/antecedents/.gitkeep wiki/behavioral/behaviors/.gitkeep wiki/behavioral/functions/.gitkeep wiki/behavioral/brain_states/.gitkeep wiki/behavioral/responses/.gitkeep wiki/behavioral/protective_factors/.gitkeep wiki/behavioral/_edges/.gitkeep
touch wiki/students/Arjun_Nair/.gitkeep wiki/students/Diya_Malhotra/.gitkeep wiki/students/Kiaan_Gupta/.gitkeep wiki/students/Mira_Shah/.gitkeep wiki/students/Saanvi_Verma/.gitkeep
touch wiki/sources/openalex/.gitkeep wiki/personas/.gitkeep
```

- [ ] **Step 2: Write `wiki/schema.md`**

Write to `wiki/schema.md`:
```markdown
# Schema — How the Agent Maintains This Wiki

This file is the agent's instruction sheet. It is read at session start and on every major rebuild. Humans may edit this file; the agent treats it as authoritative.

## Three layers

- **Raw / immutable:** `personas/`, `sources/openalex/`, the live `ingested_observations` Postgres stream. The agent reads but never modifies these (sources/openalex/ pages are written once on fetch and treated as immutable thereafter).
- **Wiki body (LLM-maintained):** `behavioral/`, `students/`. The agent owns these entirely — creates, updates, links.
- **Schema (this file) + index + log:** governance and navigation.

## The two decoupled graphs

- `behavioral/` = anonymized cross-student knowledge. Nodes for SettingEvent, Antecedent, Behavior, Function, BrainState, Response, ProtectiveFactor. Edges between them. **MUST NOT contain student names, educator names, peer names, ages, or dates.** Reinforcement is `support_count` + `students_count` integers in frontmatter.
- `students/<Name>/` = per-student named, granular knowledge. May link OUT to `behavioral/` via wikilinks. Behavioral pages NEVER link back.

## Anonymization wall

Every write to `behavioral/**` is linted by `intelligence/api/services/anonymization_lint.py`. Violations are rejected and logged. Allowed in behavioral pages: age bands ("3-4 year old"), generic actor labels ("a peer", "the guide"), behavioral terminology, anonymized prose.

## Frontmatter conventions

See `docs/superpowers/specs/2026-04-16-decoupled-kgs-and-llm-wiki-design.md` § "Frontmatter contracts" for the canonical schemas.

Behavioral node:
- `type, slug, support_count, students_count, literature_refs, curiosity_score, last_curiosity_factors, last_observed_at, last_research_fetched_at, created_at, related_nodes`

Edge file (`behavioral/_edges/<src>--<rel>--<dst>.md`):
- `src_slug, rel, dst_slug, support_count, students_count, first_observed_at, last_observed_at`
- Body: `## Evidence` section with anonymized one-liners, append-only.

Student incident:
- `student, note_id, severity, behavioral_refs, peers_present, educator, ingested_at`
- Body: `## Note` (verbatim) + `## Interpretation` (LLM).

## Page naming

- Behavioral nodes: kebab-case slug, lowercase. Example: `peer-takes-material.md`.
- Edges: `<src-type>--<src-slug>--<rel>--<dst-type>--<dst-slug>.md`. Example: `antecedents--peer-takes-material--triggers--behaviors--drops-material-and-flees.md`.
- Incidents: `YYYY-MM-DD-HHMM-<slug>.md`.

## Update protocol

On every ingested observation:
1. Write `students/<Name>/incidents/<ts>-<slug>.md` with full frontmatter.
2. For each behavioral node referenced: create if missing, increment `support_count`, increment `students_count` if this is a new student for the node, append anonymized evidence stub.
3. For each pair of co-occurring nodes in this incident: ensure edge file exists, increment edge `support_count`, append edge evidence stub.
4. Update `students/<Name>/{profile,timeline,patterns,protective_factors,relationships,log}.md` rollups.
5. Recompute `curiosity_score` for every touched behavioral node (see `intelligence/api/services/curiosity.py`).
6. Update `behavioral/_index.md` and `index.md`.
7. Append entry to `log.md` and `students/<Name>/log.md`.

## Indexing

`index.md` and `behavioral/_index.md` are auto-generated catalogs. Do not hand-edit.

`log.md` lines start with `## [YYYY-MM-DD HH:MM] <action> | <subject>` so they are grep-able with `grep "^## \[" log.md`.
```

- [ ] **Step 3: Write `wiki/index.md` initial content**

Write to `wiki/index.md`:
```markdown
# Wiki Index

> Auto-generated catalog. Do not hand-edit. Updated on every wiki write.

## Behavioral knowledge graph (anonymized)

_(empty — agent has not yet ingested any observations)_

## Students

_(empty — agent has not yet ingested any observations)_

## Personas (immutable input)

_(populated when persona docs are added under `wiki/personas/`)_

## Research sources

_(empty — agent has not yet fetched any papers)_
```

- [ ] **Step 4: Write `wiki/log.md` initial content**

Write to `wiki/log.md`:
```markdown
# Agent Activity Log

> Append-only chronological record. Format: `## [YYYY-MM-DD HH:MM] <action> | <subject>`
```

- [ ] **Step 5: Write `wiki/behavioral/_index.md` initial content**

Write to `wiki/behavioral/_index.md`:
```markdown
# Behavioral Knowledge Graph — Catalog

> Anonymized, cross-student. Auto-generated.

## Setting Events

_(empty)_

## Antecedents

_(empty)_

## Behaviors

_(empty)_

## Functions

_(empty)_

## Brain States

_(empty)_

## Responses

_(empty)_

## Protective Factors

_(empty)_

## Edges

_(empty)_
```

- [ ] **Step 6: Verify structure**

Run: `find wiki -type d | sort`
Expected: lists `wiki/behavioral/{8 subdirs}`, `wiki/students/{5 subdirs}`, `wiki/sources/openalex`, `wiki/personas`.

- [ ] **Step 7: Commit**

```bash
git add wiki/
git commit -m "phase0: scaffold wiki/ skeleton with schema, index, log, behavioral and student folders

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.3: Hand-author 5 persona docs

**Files:**
- Create: `wiki/personas/Arjun_Nair.md`, `Diya_Malhotra.md`, `Kiaan_Gupta.md`, `Mira_Shah.md`, `Saanvi_Verma.md`

- [ ] **Step 1: Write `wiki/personas/Arjun_Nair.md`**

```markdown
---
name: Arjun Nair
age_band: "4-5"
temperament_axes:
  sensory_reactivity: medium
  social_orientation: peer-seeking
  frustration_tolerance: medium
dysfunction_flavor: "impulsive"
recurring_companions: [Diya Malhotra, Kiaan Gupta]
---

# Arjun Nair

Arjun is a verbally agile four-year-old who loves the practical-life shelf — pouring, transferring, polishing — and gravitates toward older peers. He'll narrate his work out loud and invite others into it. When he's regulated, he can sustain a long work cycle and show younger children how to handle materials carefully.

When Arjun decompensates, he goes impulsive: he'll grab a peer's material, blurt across the room, or abandon a half-finished work to chase a louder activity. He rarely escalates to physical aggression; the failure mode is impulse control, not anger. Co-regulation through brief naming + a short physical reset (a glass of water, a slow breath, a return to a chosen mat) usually brings him back within a minute.
```

- [ ] **Step 2: Write `wiki/personas/Diya_Malhotra.md`**

```markdown
---
name: Diya Malhotra
age_band: "3-4"
temperament_axes:
  sensory_reactivity: high
  social_orientation: adult-seeking
  frustration_tolerance: low
dysfunction_flavor: "clingy-then-shutdown"
recurring_companions: [Arjun Nair, Saanvi Verma]
---

# Diya Malhotra

Diya is a quiet, observant three-year-old who watches a presentation two or three times before she'll attempt the work herself. She forms strong attachments to specific guides and will check in with a glance every few minutes. Her best work happens at the sensorial shelf — pink tower, brown stair, color tablets — where the feedback is concrete.

Diya's dysfunction starts as clinginess: extra check-ins, a hand on the guide's leg, a request to "do it together." If the guide is unavailable in that moment, she shuts down — sits quietly with her work untouched, refuses redirection, may cry softly. She does not externalize. The risk is that her shutdown is invisible if the guide is busy with another child, so adults need to actively scan for her.
```

- [ ] **Step 3: Write `wiki/personas/Kiaan_Gupta.md`**

```markdown
---
name: Kiaan Gupta
age_band: "4-5"
temperament_axes:
  sensory_reactivity: low
  social_orientation: independent
  frustration_tolerance: high
dysfunction_flavor: "scattered"
recurring_companions: [Arjun Nair, Mira Shah]
---

# Kiaan Gupta

Kiaan is a self-contained four-and-a-half-year-old who chooses his own work and rarely needs adult prompting. He'll spend forty minutes on a single piece of math material — bead chains, stamp game — without looking up. He's the child other parents ask about because he looks like the picture of normalization.

Kiaan's failure mode is scatter rather than aggression: when something is off (sleep, nutrition, an unsettled morning), he'll start three works without finishing any, drift between shelves, and resist returning to a single sustained activity. He doesn't disrupt others. He just dissolves his own work cycle. The intervention is environmental, not relational — narrowing his choices, sitting him next to a deeply concentrated peer, removing visual clutter.
```

- [ ] **Step 4: Write `wiki/personas/Mira_Shah.md`**

```markdown
---
name: Mira Shah
age_band: "3-4"
temperament_axes:
  sensory_reactivity: high
  social_orientation: peer-seeking
  frustration_tolerance: low
dysfunction_flavor: "explosive-then-shutdown"
recurring_companions: [Arjun Nair, Diya Malhotra]
---

# Mira Shah

Mira is a bright, energetic three-and-a-half-year-old who loves the metal insets and has just discovered moveable alphabet. She's socially confident and will recruit a friend into nearly any work. Her ideal day looks like a long peer-collaborative work cycle followed by outdoor time.

Mira's dysfunction is loud and fast. A small frustration — peer takes the cylinder she was carrying, the work doesn't fit on the first try, a transition arrives before she's ready — can flip her into screaming, throwing materials, or hitting the floor. After the explosion, she shuts down: walks to the reading corner, won't make eye contact, may stay there for ten minutes. In acute moments she can move toward objects she could throw at peers; this is the highest-risk persona and the one most likely to need emergency containment.
```

- [ ] **Step 5: Write `wiki/personas/Saanvi_Verma.md`**

```markdown
---
name: Saanvi Verma
age_band: "4-5"
temperament_axes:
  sensory_reactivity: medium
  social_orientation: adult-seeking
  frustration_tolerance: medium
dysfunction_flavor: "shutdown"
recurring_companions: [Diya Malhotra, Kiaan Gupta]
---

# Saanvi Verma

Saanvi is a methodical four-year-old who works carefully and asks clarifying questions before she begins. She's drawn to language work — sandpaper letters, moveable alphabet — and has started writing her own three-letter words. She likes to do things "right" and will redo her own work if she notices an error.

Saanvi's failure mode is freeze-and-shutdown rather than externalizing. When she encounters something she doesn't understand, or when a peer disrupts her work, she stops moving entirely. She'll stand at her work mat, look down, and not respond to verbal prompts. Adults sometimes mistake this for compliance. The intervention is patient narration — naming what she might be feeling, offering a smaller next step, not requiring a verbal response. She can recover within a few minutes if not pushed.
```

- [ ] **Step 6: Verify all five exist with frontmatter**

Run:
```bash
for p in Arjun_Nair Diya_Malhotra Kiaan_Gupta Mira_Shah Saanvi_Verma; do
  test -f "wiki/personas/$p.md" && head -1 "wiki/personas/$p.md" | grep -q '^---$' && echo "OK $p" || echo "FAIL $p"
done
```
Expected: five lines, all `OK`.

- [ ] **Step 7: Commit**

```bash
git add wiki/personas/
git commit -m "phase0: hand-author 5 persona docs (Arjun, Diya, Kiaan, Mira, Saanvi)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.4: Add new Postgres index tables (additive, alongside legacy)

**Files:**
- Modify: `intelligence/api/services/ghost_client.py`

- [ ] **Step 1: Locate `ensure_agent_tables`**

Run: `grep -n "def ensure_agent_tables" intelligence/api/services/ghost_client.py`
Expected: function exists; note line number for next step.

- [ ] **Step 2: Add new CREATE TABLE statements inside `ensure_agent_tables`**

Append the following SQL strings to the table-creation block in `ensure_agent_tables` (additive — do not remove the legacy `knowledge_graph` or `student_personality_graph` CREATE statements; those are dropped in Phase 5):

```python
            """
            CREATE TABLE IF NOT EXISTS behavioral_nodes (
                slug TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                literature_refs INT DEFAULT 0,
                curiosity_score REAL DEFAULT 0,
                curiosity_factors JSONB,
                last_observed_at TIMESTAMPTZ,
                last_research_fetched_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS behavioral_edges (
                src_slug TEXT NOT NULL,
                rel TEXT NOT NULL,
                dst_slug TEXT NOT NULL,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                first_observed_at TIMESTAMPTZ,
                last_observed_at TIMESTAMPTZ,
                file_path TEXT NOT NULL,
                PRIMARY KEY (src_slug, rel, dst_slug)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student_incidents (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                note_id INT,
                severity TEXT,
                ingested_at TIMESTAMPTZ DEFAULT NOW(),
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL,
                behavioral_ref_slugs TEXT[]
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student_profiles_index (
                student_name TEXT PRIMARY KEY,
                current_severity TEXT,
                trend TEXT,
                incident_count INT DEFAULT 0,
                patterns_summary TEXT,
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS curiosity_events (
                id BIGSERIAL PRIMARY KEY,
                node_slug TEXT NOT NULL,
                fired_at TIMESTAMPTZ DEFAULT NOW(),
                curiosity_score REAL,
                factors JSONB,
                triggered_research BOOLEAN,
                paper_count INT DEFAULT 0
            )
            """,
            """
            ALTER TABLE agent_runtime_state
                ADD COLUMN IF NOT EXISTS god_mode_overrides JSONB DEFAULT '{}'::jsonb
            """,
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile intelligence/api/services/ghost_client.py`
Expected: exit 0.

- [ ] **Step 4: Boot the API to trigger startup table creation**

Run (in one terminal):
```bash
uvicorn intelligence.api.main:app --port 8000
```

In another terminal:
```bash
curl -s http://localhost:8000/api/health | jq .status
```
Expected: `"ok"`.

- [ ] **Step 5: Verify tables exist via `psql` or Ghost CLI**

Use the connection string from `ghost_client.py`. Verify the five new tables and the new column exist:
```sql
\dt behavioral_nodes
\dt behavioral_edges
\dt student_incidents
\dt student_profiles_index
\dt curiosity_events
\d agent_runtime_state
```
Expected: all present; `agent_runtime_state` has `god_mode_overrides jsonb` column.

Stop the uvicorn process with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
git add intelligence/api/services/ghost_client.py
git commit -m "phase0: add behavioral_nodes/edges, student_incidents, student_profiles_index, curiosity_events tables and god_mode_overrides column

Additive only — legacy knowledge_graph and student_personality_graph tables remain until Phase 5.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.5: Stub new service modules (interface-only)

**Files:**
- Create: `intelligence/api/services/wiki_paths.py`
- Create: `intelligence/api/services/anonymization_lint.py`
- Create: `intelligence/api/services/wiki_writer.py`
- Create: `intelligence/api/services/wiki_indexer.py`
- Create: `intelligence/api/services/curiosity.py`
- Create: `notes_streamer/persona_engine.py`

- [ ] **Step 1: Write `intelligence/api/services/wiki_paths.py` stub**

```python
"""Path conventions and slugification for the wiki/ directory.

All wiki/-relative path construction goes through this module. No other
service should hand-build wiki paths — that's how the anonymization wall
gets bypassed by accident.
"""
from __future__ import annotations

from pathlib import Path
import re

WIKI_ROOT = Path(__file__).resolve().parents[3] / "wiki"

BEHAVIORAL_TYPES = (
    "setting_events",
    "antecedents",
    "behaviors",
    "functions",
    "brain_states",
    "responses",
    "protective_factors",
)


def slugify(text: str) -> str:
    """Return a lowercase, kebab-case slug. Stable across runs."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def behavioral_node_path(node_type: str, slug: str) -> Path:
    """Path to a behavioral node markdown file."""
    if node_type not in BEHAVIORAL_TYPES:
        raise ValueError(f"unknown behavioral type: {node_type}")
    return WIKI_ROOT / "behavioral" / node_type / f"{slug}.md"


def behavioral_edge_path(
    src_type: str, src_slug: str, rel: str, dst_type: str, dst_slug: str
) -> Path:
    """Path to a behavioral edge markdown file."""
    name = f"{src_type}--{src_slug}--{rel}--{dst_type}--{dst_slug}.md"
    return WIKI_ROOT / "behavioral" / "_edges" / name


def student_dir(student_name: str) -> Path:
    """Folder for a given student. Underscores in folder names."""
    folder = student_name.replace(" ", "_")
    return WIKI_ROOT / "students" / folder


def incident_path(student_name: str, ingested_at_iso: str, slug: str) -> Path:
    """Path to one incident page. ingested_at_iso is ISO 8601."""
    # YYYY-MM-DDTHH:MM:SS... -> YYYY-MM-DD-HHMM
    date_part = ingested_at_iso[:10]
    time_part = ingested_at_iso[11:16].replace(":", "")
    name = f"{date_part}-{time_part}-{slug}.md"
    return student_dir(student_name) / "incidents" / name


def persona_path(student_name: str) -> Path:
    folder = student_name.replace(" ", "_")
    return WIKI_ROOT / "personas" / f"{folder}.md"


def source_paper_path(openalex_id: str) -> Path:
    safe_id = openalex_id.split("/")[-1]
    return WIKI_ROOT / "sources" / "openalex" / f"{safe_id}.md"
```

- [ ] **Step 2: Write `intelligence/api/services/anonymization_lint.py` stub**

```python
"""Anonymization lint for wiki/behavioral/** writes.

Scans content for known student names, educator names, dates, and ages
that would identify a specific child. Used by wiki_writer before any
write under wiki/behavioral/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

# Keep in sync with the persona set. Updated when personas are added/removed.
KNOWN_STUDENT_NAMES = {
    "Arjun Nair",
    "Diya Malhotra",
    "Kiaan Gupta",
    "Mira Shah",
    "Saanvi Verma",
}

# Educators referenced in observation notes. Update if persona engine adds more.
KNOWN_EDUCATOR_NAMES = {
    "Amrita Maitra",
    "Sajitha Kandathil",
    "Yogitha M",
    "Hima Brijeshkumar Savaj",
    "Nandini Rao",
    "Meera Iyer",
    "Pooja Menon",
    "Anjali Deshmukh",
}

DATE_REGEX = re.compile(
    r"\b(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b"
)
TIME_REGEX = re.compile(r"\b\d{1,2}:\d{2}\b")


@dataclass
class LintViolation:
    kind: str        # "student_name" | "educator_name" | "date" | "time"
    match: str
    snippet: str


def scan(content: str) -> list[LintViolation]:
    """Return a list of violations. Empty list = clean."""
    violations: list[LintViolation] = []

    for name in KNOWN_STUDENT_NAMES:
        if name in content:
            violations.append(LintViolation("student_name", name, _snippet(content, name)))
        # Also catch first names alone (Mira, Arjun, ...)
        first = name.split()[0]
        if re.search(rf"\b{re.escape(first)}\b", content):
            violations.append(LintViolation("student_name", first, _snippet(content, first)))

    for name in KNOWN_EDUCATOR_NAMES:
        if name in content:
            violations.append(LintViolation("educator_name", name, _snippet(content, name)))

    for m in DATE_REGEX.finditer(content):
        violations.append(LintViolation("date", m.group(0), _snippet(content, m.group(0))))

    for m in TIME_REGEX.finditer(content):
        violations.append(LintViolation("time", m.group(0), _snippet(content, m.group(0))))

    return violations


def _snippet(content: str, match: str) -> str:
    idx = content.find(match)
    if idx < 0:
        return ""
    start = max(0, idx - 30)
    end = min(len(content), idx + len(match) + 30)
    return content[start:end].replace("\n", " ")


def assert_clean(content: str, *, file_path: Path) -> None:
    """Raise AnonymizationLeak if any violations found."""
    violations = scan(content)
    if violations:
        raise AnonymizationLeak(file_path, violations)


class AnonymizationLeak(Exception):
    def __init__(self, file_path: Path, violations: list[LintViolation]):
        self.file_path = file_path
        self.violations = violations
        msg_lines = [f"Anonymization leak in {file_path}:"]
        for v in violations:
            msg_lines.append(f"  - {v.kind}: '{v.match}'  (...{v.snippet}...)")
        super().__init__("\n".join(msg_lines))
```

- [ ] **Step 3: Write `intelligence/api/services/wiki_writer.py` stub**

```python
"""Markdown writer for the wiki/ directory.

Single source of truth for any write under wiki/. Enforces anonymization
on writes to wiki/behavioral/. Synchronously calls wiki_indexer after
each write so Postgres index stays in sync.

This module is a stub in Phase 0. Full implementation in Phase 2.
"""
from __future__ import annotations

from typing import Any


def write_incident(
    student_name: str,
    note_id: int,
    severity: str,
    note_body: str,
    interpretation: str,
    behavioral_refs: list[str],
    peers_present: list[str],
    educator: str,
    ingested_at_iso: str,
    slug_hint: str,
) -> str:
    """Write one student incident page. Returns the file path written."""
    raise NotImplementedError("wiki_writer.write_incident — implement in Phase 2")


def upsert_behavioral_node(
    node_type: str,
    slug: str,
    title: str,
    summary: str,
    new_evidence: str,
    new_student_name: str | None = None,
) -> dict[str, Any]:
    """Create-or-update a behavioral node. new_evidence is anonymized prose."""
    raise NotImplementedError("wiki_writer.upsert_behavioral_node — implement in Phase 2")


def upsert_behavioral_edge(
    src_type: str,
    src_slug: str,
    rel: str,
    dst_type: str,
    dst_slug: str,
    new_evidence: str,
    new_student_name: str | None = None,
) -> dict[str, Any]:
    """Create-or-update a behavioral edge."""
    raise NotImplementedError("wiki_writer.upsert_behavioral_edge — implement in Phase 2")


def update_student_rollups(student_name: str) -> None:
    """Refresh profile.md, timeline.md, patterns.md, etc. for one student."""
    raise NotImplementedError("wiki_writer.update_student_rollups — implement in Phase 2")


def append_log(action: str, subject: str, *, student_name: str | None = None) -> None:
    """Append entry to wiki/log.md (and student log if provided)."""
    raise NotImplementedError("wiki_writer.append_log — implement in Phase 2")


def update_indexes() -> None:
    """Regenerate wiki/index.md and wiki/behavioral/_index.md."""
    raise NotImplementedError("wiki_writer.update_indexes — implement in Phase 2")
```

- [ ] **Step 4: Write `intelligence/api/services/wiki_indexer.py` stub**

```python
"""Sync wiki/ markdown → Postgres index tables.

Called synchronously by wiki_writer on every write. Also exposes a full
rebuild used by the migration script and POST /api/wiki/reindex.

This module is a stub in Phase 0. Full implementation in Phase 2.
"""
from __future__ import annotations

from pathlib import Path


def index_behavioral_node(file_path: Path) -> None:
    raise NotImplementedError("wiki_indexer.index_behavioral_node — implement in Phase 2")


def index_behavioral_edge(file_path: Path) -> None:
    raise NotImplementedError("wiki_indexer.index_behavioral_edge — implement in Phase 2")


def index_student_incident(file_path: Path) -> None:
    raise NotImplementedError("wiki_indexer.index_student_incident — implement in Phase 2")


def index_student_profile(file_path: Path) -> None:
    raise NotImplementedError("wiki_indexer.index_student_profile — implement in Phase 2")


def full_rebuild() -> dict[str, int]:
    """Walk wiki/, drop and replay all index tables. Returns counts."""
    raise NotImplementedError("wiki_indexer.full_rebuild — implement in Phase 2")
```

- [ ] **Step 5: Write `intelligence/api/services/curiosity.py` stub**

```python
"""Quantifiable curiosity score + research-firing gate.

Six signals: novelty, recurrence_gap, cross_student, surprise,
severity_weight, recency. Composite score in [0, 1]. Gate fires research
when score >= 0.70 and 30-min cooldown elapsed.

This module is a stub in Phase 0. Full implementation in Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_WEIGHTS = {
    "novelty": 0.20,
    "recurrence_gap": 0.20,
    "cross_student": 0.20,
    "surprise": 0.15,
    "severity_weight": 0.15,
    "recency": 0.10,
}

CURIOSITY_THRESHOLD = 0.70
COOLDOWN_MINUTES = 30


@dataclass
class CuriosityFactors:
    novelty: float
    recurrence_gap: float
    cross_student: float
    surprise: float
    severity_weight: float
    recency: float

    def score(self, weights: dict[str, float] = DEFAULT_WEIGHTS) -> float:
        return (
            weights["novelty"] * self.novelty
            + weights["recurrence_gap"] * self.recurrence_gap
            + weights["cross_student"] * self.cross_student
            + weights["surprise"] * self.surprise
            + weights["severity_weight"] * self.severity_weight
            + weights["recency"] * self.recency
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "novelty": self.novelty,
            "recurrence_gap": self.recurrence_gap,
            "cross_student": self.cross_student,
            "surprise": self.surprise,
            "severity_weight": self.severity_weight,
            "recency": self.recency,
        }


def compute_factors(node_slug: str, recent_evidence_text: str | None = None) -> CuriosityFactors:
    raise NotImplementedError("curiosity.compute_factors — implement in Phase 3")


def evaluate_gate(node_slug: str) -> dict:
    """Return {fire: bool, score: float, factors: dict, reason: str}."""
    raise NotImplementedError("curiosity.evaluate_gate — implement in Phase 3")
```

- [ ] **Step 6: Write `notes_streamer/persona_engine.py` stub**

```python
"""LLM-driven note generator conditioned on persona + recent context.

Replaces the static-corpus generator (scripts/generate_notes_corpus.py).
Called by the streamer on each tick, and by POST /api/persona/next-note.

This module is a stub in Phase 0. Full implementation in Phase 1.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaOverrides:
    slider: float = 0.0           # -1.0 functional .. +1.0 dysfunctional
    flavor_override: str | None = None
    activity_weight: float = 1.0
    inject_next: str | None = None  # "neutral" | "problematic" | "emergency" | "surprise"
    interact_with: str | None = None
    interact_scene_hint: str | None = None


def generate_next_note(student_name: str, overrides: PersonaOverrides | None = None) -> dict:
    """Return {name, body, severity_hint}. Caller inserts into ingested_observations."""
    raise NotImplementedError("persona_engine.generate_next_note — implement in Phase 1")


def list_personas() -> list[dict]:
    """Return persona summaries from wiki/personas/*.md including current overrides."""
    raise NotImplementedError("persona_engine.list_personas — implement in Phase 1")
```

- [ ] **Step 7: Verify all stubs compile**

Run:
```bash
python3 -m py_compile \
  intelligence/api/services/wiki_paths.py \
  intelligence/api/services/anonymization_lint.py \
  intelligence/api/services/wiki_writer.py \
  intelligence/api/services/wiki_indexer.py \
  intelligence/api/services/curiosity.py \
  notes_streamer/persona_engine.py
```
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add intelligence/api/services/wiki_paths.py intelligence/api/services/anonymization_lint.py intelligence/api/services/wiki_writer.py intelligence/api/services/wiki_indexer.py intelligence/api/services/curiosity.py notes_streamer/persona_engine.py
git commit -m "phase0: stub wiki_paths, anonymization_lint, wiki_writer, wiki_indexer, curiosity, persona_engine

Anonymization lint is fully implemented (pure function, no DB).
wiki_paths is fully implemented (pure path utility).
Other modules raise NotImplementedError; concrete behavior arrives in Phases 1-3.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.6: Add Phase-0 API endpoints (empty payloads — let the visualizer develop in parallel)

**Files:**
- Modify: `intelligence/api/main.py`
- Modify: `intelligence/api/services/ghost_client.py` (add helpers used by new endpoints)

- [ ] **Step 1: Add empty-payload helpers to `ghost_client.py`**

Append to `intelligence/api/services/ghost_client.py`:
```python
def list_behavioral_nodes() -> list[dict]:
    """Return all rows from behavioral_nodes index. Empty list if none."""
    with _connect_agent_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT slug, type, title, summary, support_count, students_count, "
                "literature_refs, curiosity_score, curiosity_factors, "
                "last_observed_at, last_research_fetched_at, created_at, file_path "
                "FROM behavioral_nodes ORDER BY support_count DESC"
            )
            return [dict(row) for row in cur.fetchall()]


def list_behavioral_edges(min_support: int = 1) -> list[dict]:
    with _connect_agent_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT src_slug, rel, dst_slug, support_count, students_count, "
                "first_observed_at, last_observed_at "
                "FROM behavioral_edges WHERE support_count >= %s",
                (min_support,),
            )
            return [dict(row) for row in cur.fetchall()]


def list_student_incidents(student_name: str, limit: int = 50) -> list[dict]:
    with _connect_agent_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, student_name, note_id, severity, ingested_at, file_path, "
                "behavioral_ref_slugs "
                "FROM student_incidents WHERE student_name = %s "
                "ORDER BY ingested_at DESC LIMIT %s",
                (student_name, limit),
            )
            return [dict(row) for row in cur.fetchall()]


def list_curiosity_events(limit: int = 50) -> list[dict]:
    with _connect_agent_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, node_slug, fired_at, curiosity_score, factors, "
                "triggered_research, paper_count "
                "FROM curiosity_events ORDER BY fired_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_runtime_overrides() -> dict:
    """Return agent_runtime_state.god_mode_overrides as a dict (empty if null)."""
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT god_mode_overrides FROM agent_runtime_state ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else {}


def set_runtime_overrides(overrides: dict) -> None:
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_runtime_state SET god_mode_overrides = %s "
                "WHERE id = (SELECT id FROM agent_runtime_state ORDER BY id DESC LIMIT 1)",
                (psycopg2.extras.Json(overrides),),
            )
            conn.commit()
```

If `psycopg2.extras` is not already imported at the top of `ghost_client.py`, add `import psycopg2.extras` to the imports. If `_connect_agent_db` is the wrong helper name, look at the existing helpers in the file and use the established pattern (e.g., `_get_agent_conn`).

- [ ] **Step 2: Add new endpoints to `intelligence/api/main.py`**

Import the new helpers near the existing `get_alerts` import:
```python
from intelligence.api.services.ghost_client import (
    # ... existing imports ...
    list_behavioral_nodes,
    list_behavioral_edges,
    list_student_incidents,
    list_curiosity_events,
    get_runtime_overrides,
    set_runtime_overrides,
)
```

Append the following endpoint blocks at the bottom of `intelligence/api/main.py`:
```python
# ── Phase 0: empty/index-backed endpoints. Real behavior wired in Phases 1-3. ──

@app.get("/api/behavioral-graph")
def behavioral_graph(min_support: int = 1):
    nodes = list_behavioral_nodes()
    edges = list_behavioral_edges(min_support=min_support)
    return {"nodes": nodes, "edges": edges}


@app.get("/api/student-graph/{student_name}")
def student_graph(student_name: str, limit: int = 50):
    incidents = list_student_incidents(student_name, limit=limit)
    return {"student_name": student_name, "incidents": incidents}


@app.get("/api/student-graph/{student_name}/research")
def student_graph_research(student_name: str):
    # Phase 0: returns existing literature rows. Phase 3 enriches via wiki sources/openalex/.
    return {"student_name": student_name, "papers": get_student_literature(student_name)}


@app.get("/api/personas")
def personas():
    from notes_streamer.persona_engine import list_personas
    try:
        return {"personas": list_personas(), "overrides": get_runtime_overrides()}
    except NotImplementedError:
        return {"personas": [], "overrides": get_runtime_overrides(), "stub": True}


class PersonaUpdate(BaseModel):
    slider: float | None = None
    flavor_override: str | None = None
    activity_weight: float | None = None


@app.patch("/api/personas/{student_name}")
def update_persona(student_name: str, payload: PersonaUpdate):
    overrides = get_runtime_overrides()
    student_block = overrides.get(student_name, {})
    if payload.slider is not None:
        student_block["slider"] = payload.slider
    if payload.flavor_override is not None:
        student_block["flavor_override"] = payload.flavor_override
    if payload.activity_weight is not None:
        student_block["activity_weight"] = payload.activity_weight
    overrides[student_name] = student_block
    set_runtime_overrides(overrides)
    return {"student_name": student_name, "overrides": student_block}


class InjectRequest(BaseModel):
    flavor: str  # "neutral" | "problematic" | "emergency" | "surprise"


@app.post("/api/personas/{student_name}/inject")
def inject_persona(student_name: str, payload: InjectRequest):
    overrides = get_runtime_overrides()
    block = overrides.get(student_name, {})
    block["inject_next"] = payload.flavor
    overrides[student_name] = block
    set_runtime_overrides(overrides)
    return {"student_name": student_name, "inject_next": payload.flavor}


class InteractRequest(BaseModel):
    a: str
    b: str
    scene_hint: str | None = None


@app.post("/api/personas/interact")
def interact_personas(payload: InteractRequest):
    overrides = get_runtime_overrides()
    for name in (payload.a, payload.b):
        block = overrides.get(name, {})
        block["interact_with"] = payload.b if name == payload.a else payload.a
        if payload.scene_hint:
            block["interact_scene_hint"] = payload.scene_hint
        overrides[name] = block
    set_runtime_overrides(overrides)
    return {"a": payload.a, "b": payload.b}


class NextNoteRequest(BaseModel):
    student_name: str


@app.post("/api/persona/next-note")
def persona_next_note(payload: NextNoteRequest):
    from notes_streamer.persona_engine import generate_next_note, PersonaOverrides
    overrides = get_runtime_overrides().get(payload.student_name, {})
    po = PersonaOverrides(**{k: v for k, v in overrides.items() if k in PersonaOverrides.__dataclass_fields__})
    try:
        note = generate_next_note(payload.student_name, overrides=po)
        return note
    except NotImplementedError:
        raise HTTPException(503, "persona_engine not yet implemented (Phase 1)")


@app.get("/api/curiosity/events")
def curiosity_events_endpoint(limit: int = 50):
    return {"events": list_curiosity_events(limit=limit)}


class CuriosityWeightUpdate(BaseModel):
    novelty: float | None = None
    recurrence_gap: float | None = None
    cross_student: float | None = None
    surprise: float | None = None
    severity_weight: float | None = None
    recency: float | None = None


@app.patch("/api/runtime/curiosity-weights")
def update_curiosity_weights(payload: CuriosityWeightUpdate):
    overrides = get_runtime_overrides()
    weights = overrides.get("_curiosity_weights", {})
    for k, v in payload.dict(exclude_none=True).items():
        weights[k] = v
    overrides["_curiosity_weights"] = weights
    set_runtime_overrides(overrides)
    return {"curiosity_weights": weights}


@app.post("/api/curiosity/recompute/{slug}")
def curiosity_recompute(slug: str):
    from intelligence.api.services.curiosity import compute_factors
    try:
        factors = compute_factors(slug)
        return {"slug": slug, "factors": factors.to_dict(), "score": factors.score()}
    except NotImplementedError:
        raise HTTPException(503, "curiosity.compute_factors not yet implemented (Phase 3)")


@app.post("/api/curiosity/investigate/{slug}")
def curiosity_investigate(slug: str):
    try:
        from intelligence.api.services.curiosity import evaluate_gate
        result = evaluate_gate(slug)
        return result
    except NotImplementedError:
        raise HTTPException(503, "curiosity.evaluate_gate not yet implemented (Phase 3)")


@app.get("/api/wiki/tree")
def wiki_tree():
    from intelligence.api.services.wiki_paths import WIKI_ROOT
    tree: list[dict] = []
    for path in sorted(WIKI_ROOT.rglob("*.md")):
        rel = path.relative_to(WIKI_ROOT).as_posix()
        tree.append({"path": rel, "mtime": path.stat().st_mtime})
    return {"root": str(WIKI_ROOT), "files": tree}


@app.get("/api/wiki/page")
def wiki_page(path: str):
    from intelligence.api.services.wiki_paths import WIKI_ROOT
    target = (WIKI_ROOT / path).resolve()
    if not str(target).startswith(str(WIKI_ROOT.resolve())):
        raise HTTPException(400, "path traversal blocked")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, f"no such wiki page: {path}")
    raw = target.read_text(encoding="utf-8")
    # Frontmatter parsing — Phase 2 will add backlinks computation. Phase 0 returns raw.
    try:
        import frontmatter
        post = frontmatter.loads(raw)
        return {"path": path, "frontmatter": post.metadata, "body": post.content, "raw": raw}
    except Exception:
        return {"path": path, "frontmatter": {}, "body": raw, "raw": raw}


@app.post("/api/wiki/reindex")
def wiki_reindex():
    try:
        from intelligence.api.services.wiki_indexer import full_rebuild
        return full_rebuild()
    except NotImplementedError:
        raise HTTPException(503, "wiki_indexer.full_rebuild not yet implemented (Phase 2)")
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile intelligence/api/main.py intelligence/api/services/ghost_client.py`
Expected: exit 0.

- [ ] **Step 4: Boot the API and exercise the new empty endpoints**

```bash
uvicorn intelligence.api.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/behavioral-graph | jq .
curl -s http://localhost:8000/api/student-graph/Mira%20Shah | jq .
curl -s http://localhost:8000/api/curiosity/events | jq .
curl -s http://localhost:8000/api/wiki/tree | jq '.files | length'
curl -s "http://localhost:8000/api/wiki/page?path=schema.md" | jq '.frontmatter, .path'
curl -s -X PATCH http://localhost:8000/api/personas/Mira%20Shah -H "Content-Type: application/json" -d '{"slider": 0.7}' | jq .
curl -s -X POST http://localhost:8000/api/personas/Mira%20Shah/inject -H "Content-Type: application/json" -d '{"flavor": "emergency"}' | jq .
kill %1
```
Expected:
- behavioral-graph: `{"nodes": [], "edges": []}`
- student-graph: `{"student_name": "Mira Shah", "incidents": []}`
- curiosity/events: `{"events": []}`
- wiki/tree: integer ≥ 4 (schema/index/log + behavioral/_index)
- wiki/page schema.md: frontmatter empty (it's a doc, not a data page), path returned
- PATCH persona: returns `{"student_name": "Mira Shah", "overrides": {"slider": 0.7}}`
- POST inject: returns `{"student_name": "Mira Shah", "inject_next": "emergency"}`

- [ ] **Step 5: Commit**

```bash
git add intelligence/api/main.py intelligence/api/services/ghost_client.py
git commit -m "phase0: add stub endpoints for behavioral graph, student graph, personas, curiosity, wiki

All endpoints either return empty payloads or raise 503 with 'implement in
Phase N'. Lets the visualizer (Phase 4) develop in parallel against the
shape of real responses.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.7: Verify existing demo still works unchanged

Goal: make sure Phase 0 was truly additive.

- [ ] **Step 1: Run the existing demo flow end-to-end**

Boot API, dashboard, and visualizer:
```bash
uvicorn intelligence.api.main:app --port 8000 &
cd frontend && npm run dev &
cd ../backend_visualizer && npm run dev &
```

- [ ] **Step 2: Open the visualizer and click Start**

Open `http://localhost:3200`. Click `Start Live Demo` (existing flow).

Expected: notes appear, profiles update, alerts fire, KG nodes appear (from legacy `knowledge_graph` table) — exactly as before. Nothing in the new behavioral/ wiki tree should populate yet (Phase 2 wires that).

- [ ] **Step 3: Stop processes**

Ctrl-C all three.

- [ ] **Step 4: No new commit needed if everything works**

If anything is broken, file the failure in the task notes and fix before proceeding to Phase 1.

---

**End of Phase 0.** Phases 1, 2, and 4 are now unblocked and can run in parallel via subagents. Phase 3 waits for Phase 2.

---

## Phase 1 — Persona engine (parallel-safe with Phase 2)

Goal: replace the static-corpus streamer with a live LLM-driven persona engine that respects the God Mode overrides set by Phase 0 endpoints.

### Task 1.1: Implement `persona_engine.list_personas()`

**Files:**
- Modify: `notes_streamer/persona_engine.py`

- [ ] **Step 1: Replace the stub `list_personas` with a real implementation**

Replace the `list_personas` stub in `notes_streamer/persona_engine.py` with:
```python
import frontmatter
from intelligence.api.services.wiki_paths import WIKI_ROOT


def list_personas() -> list[dict]:
    """Return persona summaries from wiki/personas/*.md."""
    personas_dir = WIKI_ROOT / "personas"
    out: list[dict] = []
    for path in sorted(personas_dir.glob("*.md")):
        post = frontmatter.load(path)
        out.append({
            "name": post.metadata.get("name", path.stem.replace("_", " ")),
            "age_band": post.metadata.get("age_band"),
            "temperament_axes": post.metadata.get("temperament_axes", {}),
            "dysfunction_flavor": post.metadata.get("dysfunction_flavor"),
            "recurring_companions": post.metadata.get("recurring_companions", []),
            "narrative": post.content.strip(),
            "file_path": str(path.relative_to(WIKI_ROOT)),
        })
    return out
```

- [ ] **Step 2: Verify**

```bash
python3 -c "from notes_streamer.persona_engine import list_personas; import json; print(json.dumps([p['name'] for p in list_personas()]))"
```
Expected: `["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]`.

- [ ] **Step 3: Verify endpoint now returns populated personas**

Boot API, then:
```bash
curl -s http://localhost:8000/api/personas | jq '.personas | length'
```
Expected: `5`.

- [ ] **Step 4: Commit**

```bash
git add notes_streamer/persona_engine.py
git commit -m "phase1: implement persona_engine.list_personas reading wiki/personas/*.md

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.2: Implement `persona_engine.generate_next_note()`

**Files:**
- Modify: `notes_streamer/persona_engine.py`

- [ ] **Step 1: Add LLM helper + recent-context loader**

Append to `notes_streamer/persona_engine.py`:
```python
import os
from openai import OpenAI

from intelligence.api.services.ghost_client import (
    list_student_incidents,
    get_student_profile,
)


def _openai_client() -> OpenAI | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    return OpenAI(api_key=key)


def _persona_block(student_name: str) -> dict | None:
    for p in list_personas():
        if p["name"] == student_name:
            return p
    return None


def _recent_own_incidents(student_name: str, limit: int = 3) -> list[str]:
    """Return recent incident body texts for this student. Empty list if none."""
    incidents = list_student_incidents(student_name, limit=limit)
    out: list[str] = []
    for inc in incidents:
        try:
            from pathlib import Path
            text = Path(inc["file_path"]).read_text(encoding="utf-8")
            # Just include the body markdown, not the YAML frontmatter
            if "---" in text:
                _, _, body = text.partition("---")
                _, _, body = body.partition("---")
                out.append(body.strip()[:600])
            else:
                out.append(text[:600])
        except Exception:
            continue
    return out


def _recent_companion_incidents(persona: dict, limit: int = 3) -> list[str]:
    """Return recent incidents involving recurring companions."""
    out: list[str] = []
    for companion in persona.get("recurring_companions", []):
        out.extend(_recent_own_incidents(companion, limit=1))
        if len(out) >= limit:
            break
    return out[:limit]
```

- [ ] **Step 2: Implement `generate_next_note`**

Replace the `generate_next_note` stub with:
```python
def generate_next_note(
    student_name: str, overrides: PersonaOverrides | None = None
) -> dict:
    """Return {name, body, severity_hint}. Caller inserts into ingested_observations."""
    overrides = overrides or PersonaOverrides()
    persona = _persona_block(student_name)
    if not persona:
        raise ValueError(f"no persona found for {student_name}")

    own = _recent_own_incidents(student_name)
    companions = _recent_companion_incidents(persona)

    # If God Mode injected a one-shot directive, it overrides slider behavior.
    inject = overrides.inject_next

    # Translate slider to qualitative band the LLM can use.
    s = overrides.slider
    band = (
        "deeply normalized and concentrated" if s < -0.6
        else "settled and engaged" if s < -0.2
        else "ordinary and mixed" if s < 0.2
        else "frayed and emotionally close to the surface" if s < 0.6
        else "acutely dysregulated, near-emergency"
    )
    flavor = overrides.flavor_override or persona.get("dysfunction_flavor", "scattered")

    interaction_clause = ""
    if overrides.interact_with:
        interaction_clause = (
            f"\n\nThis observation must include {overrides.interact_with} as a peer "
            f"in a meaningful interaction"
            f"{(' — scene hint: ' + overrides.interact_scene_hint) if overrides.interact_scene_hint else ''}."
        )

    inject_clause = ""
    severity_hint = "neutral"
    if inject == "neutral":
        inject_clause = "\n\nThis specific observation should be a quiet, neutral, normalized work-cycle moment regardless of the slider state."
        severity_hint = "green"
    elif inject == "problematic":
        inject_clause = "\n\nThis specific observation must show a clear behavioral concern that needed adult intervention."
        severity_hint = "yellow"
    elif inject == "emergency":
        inject_clause = (
            "\n\nThis specific observation must be an EMERGENCY — explicit threats, "
            "self-harm language, or movement toward weapons or peers in a way that required "
            "two adults to contain. Use unambiguous language so the agent's emergency triggers fire."
        )
        severity_hint = "red"
    elif inject == "surprise":
        inject_clause = "\n\nThis specific observation should surprise the reader — go against the established pattern in this child's recent notes in a plausible way."
        severity_hint = "yellow"

    own_block = "\n---\n".join(own) if own else "(no prior observations for this child yet)"
    comp_block = "\n---\n".join(companions) if companions else "(no recent peer-context available)"

    system = (
        "You are an experienced Montessori guide writing a single classroom observation note "
        "about one specific child. Notes are 2-3 short paragraphs of natural prose. They begin "
        "with 'Name: <child full name>' on its own line, then a blank line, then the observation. "
        "Use real Montessori vocabulary (work cycle, presentation, normalization, sensorial, "
        "practical life, moveable alphabet, transitions). Do NOT add headings, bullets, "
        "interpretation, plans, or commentary outside the observation itself. Do NOT mention "
        "previous notes or the agent watching."
    )

    user = f"""Write one observation note for the following child.

PERSONA:
Name: {persona['name']}
Age band: {persona['age_band']}
Dysfunction flavor (when stressed): {flavor}
Persona narrative:
{persona['narrative']}

CURRENT REGULATORY STATE: this child is currently {band}.

RECENT OBSERVATIONS OF THIS CHILD (most recent first, may be empty):
{own_block}

RECENT OBSERVATIONS INVOLVING RECURRING COMPANIONS:
{comp_block}
{interaction_clause}{inject_clause}

Output exactly the note in the format:

Name: {persona['name']}

<observation paragraphs>
"""

    client = _openai_client()
    if client is None:
        # Fallback: cheap deterministic template so the demo doesn't break without an API key.
        body = (
            f"Name: {persona['name']}\n\n"
            f"{persona['name']} chose a familiar work and proceeded with steady attention. "
            f"The child maintained a calm body and used the material respectfully throughout the cycle. "
            f"By the end of the observation the child had returned the material to the shelf in order.\n"
        )
        return {"name": persona['name'], "body": body, "severity_hint": "green"}

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.9,
        max_tokens=400,
    )
    body = resp.choices[0].message.content.strip()
    if not body.startswith("Name:"):
        body = f"Name: {persona['name']}\n\n{body}"
    return {"name": persona["name"], "body": body + ("\n" if not body.endswith("\n") else ""), "severity_hint": severity_hint}
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile notes_streamer/persona_engine.py`
Expected: exit 0.

- [ ] **Step 4: Write `scripts/verify_persona_engine.py`**

```python
"""Verify persona engine returns structurally valid notes for all 5 personas."""
import sys
from notes_streamer.persona_engine import generate_next_note, PersonaOverrides

NAMES = ["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]

def main() -> int:
    failures: list[str] = []
    for name in NAMES:
        try:
            note = generate_next_note(name, overrides=PersonaOverrides(slider=0.0))
        except Exception as e:
            failures.append(f"{name}: exception {e!r}")
            continue
        if note.get("name") != name:
            failures.append(f"{name}: returned wrong name {note.get('name')!r}")
        body = note.get("body") or ""
        if not body.startswith("Name:"):
            failures.append(f"{name}: body missing 'Name:' header")
        if name not in body:
            failures.append(f"{name}: body missing the child's name")

    # Inject test
    try:
        emerg = generate_next_note("Mira Shah", overrides=PersonaOverrides(inject_next="emergency"))
        if emerg.get("severity_hint") != "red":
            failures.append("emergency inject did not set severity_hint=red")
    except Exception as e:
        failures.append(f"emergency inject exception: {e!r}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print(f"OK — generated {len(NAMES)} notes + 1 emergency inject")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run verification**

Run: `python3 -m scripts.verify_persona_engine`
Expected: `OK — generated 5 notes + 1 emergency inject`. Exit 0.

(If `OPENAI_API_KEY` is unset, the fallback template path runs and should still satisfy the structural assertions.)

- [ ] **Step 6: Commit**

```bash
git add notes_streamer/persona_engine.py scripts/verify_persona_engine.py
git commit -m "phase1: implement persona_engine.generate_next_note with LLM + fallback

LLM context: persona doc + recent own incidents + companion incidents +
slider state band + one-shot inject directive + interaction clause.
Falls back to a cheap template when OPENAI_API_KEY is unset.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.3: Wire streamer to persona engine

**Files:**
- Modify: `notes_streamer/streamer.py`

- [ ] **Step 1: Inspect current streamer logic**

Run: `cat notes_streamer/streamer.py | head -120`

Find the loop that picks a `.txt` file from `notes_streamer/notes/` and inserts into `ingested_observations`. That's the path being replaced.

- [ ] **Step 2: Replace the file-picker with persona engine call**

Locate the function that does the per-tick insertion (likely a `stream_notes` or `_stream_loop` function). Replace the file-read block with:

```python
import random
import time

from notes_streamer.persona_engine import generate_next_note, PersonaOverrides, list_personas
from intelligence.api.services.ghost_client import (
    insert_observation,           # if this helper exists; otherwise inline the SQL as before
    get_runtime_overrides,
)


def _pick_persona() -> dict:
    """Pick a persona weighted by activity_weight (default 1.0)."""
    personas = list_personas()
    overrides = get_runtime_overrides()
    weighted: list[tuple[dict, float]] = []
    for p in personas:
        block = overrides.get(p["name"], {})
        w = float(block.get("activity_weight", 1.0))
        if w <= 0:
            continue
        weighted.append((p, w))
    if not weighted:
        # All personas paused — fall back to picking at random anyway so the loop doesn't stall.
        return random.choice(personas)
    total = sum(w for _, w in weighted)
    r = random.uniform(0, total)
    upto = 0.0
    for p, w in weighted:
        upto += w
        if upto >= r:
            return p
    return weighted[-1][0]


def stream_one_note() -> None:
    """Generate and insert one persona-driven observation."""
    persona = _pick_persona()
    overrides_block = get_runtime_overrides().get(persona["name"], {})
    po = PersonaOverrides(
        slider=float(overrides_block.get("slider", 0.0)),
        flavor_override=overrides_block.get("flavor_override"),
        activity_weight=float(overrides_block.get("activity_weight", 1.0)),
        inject_next=overrides_block.get("inject_next"),
        interact_with=overrides_block.get("interact_with"),
        interact_scene_hint=overrides_block.get("interact_scene_hint"),
    )
    note = generate_next_note(persona["name"], overrides=po)
    insert_observation(name=note["name"], body=note["body"])

    # Clear one-shot fields so they don't repeat next tick.
    if overrides_block.get("inject_next") or overrides_block.get("interact_with"):
        from intelligence.api.services.ghost_client import set_runtime_overrides
        ov = get_runtime_overrides()
        block = ov.get(persona["name"], {})
        block.pop("inject_next", None)
        block.pop("interact_with", None)
        block.pop("interact_scene_hint", None)
        ov[persona["name"]] = block
        set_runtime_overrides(ov)
```

If `insert_observation` does not yet exist in `ghost_client.py`, add it:
```python
def insert_observation(name: str, body: str) -> int:
    with _connect_notes_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ingested_observations (name, body) VALUES (%s, %s) "
                "ON CONFLICT (name, body) DO UPDATE SET body = EXCLUDED.body "
                "RETURNING id",
                (name, body),
            )
            row = cur.fetchone()
            conn.commit()
            return row[0]
```

Also update the streamer's main loop to use `stream_one_note()` on each tick with cadence `random.uniform(2.0, 8.0)` between ticks. Remove the static-corpus directory walking. Leave the static `.txt` files in `notes_streamer/notes/` on disk for now — they get removed in Phase 5.

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile notes_streamer/streamer.py intelligence/api/services/ghost_client.py`
Expected: exit 0.

- [ ] **Step 4: Live run test**

Boot API and streamer:
```bash
uvicorn intelligence.api.main:app --port 8000 &
sleep 1
python3 -m notes_streamer.streamer &
STREAM_PID=$!
sleep 25
# Should have generated ~3-12 notes in 25 seconds
kill $STREAM_PID
```

Then verify rows arrived:
```bash
curl -s http://localhost:8000/api/health | jq .
# Inspect ingested_observations directly via your DB tool. Expected: at least 3 new rows
# distributed across the 5 persona names.
```

- [ ] **Step 5: Commit**

```bash
git add notes_streamer/streamer.py intelligence/api/services/ghost_client.py
git commit -m "phase1: wire streamer to persona_engine; remove static-corpus path

Streamer picks persona weighted by activity_weight, calls generate_next_note,
inserts result. One-shot inject/interact fields are cleared after consumption.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

**End of Phase 1.** Persona engine + streamer are live. Next, Phase 2 builds the wiki writer that turns ingested notes into markdown.

---

## Phase 2 — Wiki writer + indexer (parallel-safe with Phase 1)

Goal: every ingested observation becomes a markdown incident page; behavioral nodes/edges are created/updated; student rollups refresh; Postgres index stays in sync; anonymization is enforced.

### Task 2.1: Implement `wiki_writer.append_log` and `wiki_writer.update_indexes`

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py`

These are the simplest operations and used by every other write — implement them first.

- [ ] **Step 1: Replace `append_log` and `update_indexes` stubs**

Replace those two functions in `wiki_writer.py` with:
```python
from datetime import datetime, timezone
from pathlib import Path

from intelligence.api.services.wiki_paths import WIKI_ROOT, BEHAVIORAL_TYPES


def append_log(action: str, subject: str, *, student_name: str | None = None) -> None:
    """Append entry to wiki/log.md (and student log if provided)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    line = f"## [{ts}] {action} | {subject}\n"

    log_path = WIKI_ROOT / "log.md"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)

    if student_name:
        sdir = WIKI_ROOT / "students" / student_name.replace(" ", "_")
        sdir.mkdir(parents=True, exist_ok=True)
        student_log = sdir / "log.md"
        if not student_log.exists():
            student_log.write_text(f"# {student_name} — Agent Log\n\n", encoding="utf-8")
        with student_log.open("a", encoding="utf-8") as f:
            f.write(line)


def update_indexes() -> None:
    """Regenerate wiki/index.md and wiki/behavioral/_index.md from disk state."""
    _write_root_index()
    _write_behavioral_index()


def _write_root_index() -> None:
    sections: list[str] = ["# Wiki Index\n", "> Auto-generated catalog. Do not hand-edit.\n"]

    sections.append("\n## Behavioral knowledge graph (anonymized)\n")
    behavioral_root = WIKI_ROOT / "behavioral"
    has_any = False
    for ntype in BEHAVIORAL_TYPES:
        type_dir = behavioral_root / ntype
        files = sorted(type_dir.glob("*.md"))
        if not files:
            continue
        has_any = True
        sections.append(f"\n### {ntype.replace('_', ' ').title()}\n")
        for f in files:
            slug = f.stem
            sections.append(f"- [{slug}](behavioral/{ntype}/{f.name})\n")
    if not has_any:
        sections.append("\n_(empty)_\n")

    sections.append("\n## Students\n")
    students_root = WIKI_ROOT / "students"
    student_dirs = sorted([p for p in students_root.iterdir() if p.is_dir()])
    if student_dirs:
        for sdir in student_dirs:
            display = sdir.name.replace("_", " ")
            inc_count = len(list((sdir / "incidents").glob("*.md"))) if (sdir / "incidents").exists() else 0
            sections.append(f"- [{display}](students/{sdir.name}/profile.md) — {inc_count} incident(s)\n")
    else:
        sections.append("\n_(empty)_\n")

    sections.append("\n## Personas (immutable input)\n")
    personas_dir = WIKI_ROOT / "personas"
    for f in sorted(personas_dir.glob("*.md")):
        sections.append(f"- [{f.stem.replace('_', ' ')}](personas/{f.name})\n")

    sections.append("\n## Research sources\n")
    sources_dir = WIKI_ROOT / "sources" / "openalex"
    papers = sorted(sources_dir.glob("*.md"))
    if papers:
        for f in papers:
            sections.append(f"- [{f.stem}](sources/openalex/{f.name})\n")
    else:
        sections.append("\n_(empty)_\n")

    (WIKI_ROOT / "index.md").write_text("".join(sections), encoding="utf-8")


def _write_behavioral_index() -> None:
    sections: list[str] = [
        "# Behavioral Knowledge Graph — Catalog\n",
        "> Anonymized, cross-student. Auto-generated.\n",
    ]
    behavioral_root = WIKI_ROOT / "behavioral"
    for ntype in BEHAVIORAL_TYPES:
        title = ntype.replace("_", " ").title()
        sections.append(f"\n## {title}\n")
        type_dir = behavioral_root / ntype
        files = sorted(type_dir.glob("*.md"))
        if not files:
            sections.append("\n_(empty)_\n")
            continue
        for f in files:
            sections.append(f"- [{f.stem}]({ntype}/{f.name})\n")

    sections.append("\n## Edges\n")
    edges_dir = behavioral_root / "_edges"
    edges = sorted(edges_dir.glob("*.md"))
    if edges:
        for f in edges:
            sections.append(f"- [{f.stem}](_edges/{f.name})\n")
    else:
        sections.append("\n_(empty)_\n")

    (behavioral_root / "_index.md").write_text("".join(sections), encoding="utf-8")
```

- [ ] **Step 2: Smoke test**

```bash
python3 -c "
from intelligence.api.services.wiki_writer import append_log, update_indexes
append_log('test', 'phase2 smoke')
update_indexes()
print('ok')
"
tail -3 wiki/log.md
head -20 wiki/index.md
```
Expected: `ok`; log has the test line; index lists personas under "Personas (immutable input)".

- [ ] **Step 3: Commit**

```bash
git add intelligence/api/services/wiki_writer.py
git commit -m "phase2: implement wiki_writer.append_log and update_indexes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.2: Implement `wiki_writer.upsert_behavioral_node` with anonymization lint

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py`

- [ ] **Step 1: Replace the `upsert_behavioral_node` stub**

Replace with:
```python
import frontmatter
from threading import Lock

from intelligence.api.services.anonymization_lint import assert_clean
from intelligence.api.services.wiki_paths import behavioral_node_path

_WRITE_LOCK = Lock()


def upsert_behavioral_node(
    node_type: str,
    slug: str,
    title: str,
    summary: str,
    new_evidence: str,
    new_student_name: str | None = None,
) -> dict:
    """Create-or-update a behavioral node. new_evidence must be anonymized prose."""
    with _WRITE_LOCK:
        path = behavioral_node_path(node_type, slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        if path.exists():
            post = frontmatter.load(path)
            meta = post.metadata
            body = post.content
        else:
            meta = {
                "type": node_type.rstrip("s") if node_type.endswith("s") else node_type,
                "slug": slug,
                "support_count": 0,
                "students_count": 0,
                "students_seen": [],   # internal — stripped before write to enforce anonymization? No: this stays under students_count derivation.
                "literature_refs": 0,
                "curiosity_score": 0.0,
                "last_curiosity_factors": {},
                "last_observed_at": None,
                "last_research_fetched_at": None,
                "created_at": now,
                "related_nodes": [],
            }
            body = f"# {title}\n\n## Summary\n\n{summary}\n\n## Evidence\n\n"

        meta["support_count"] = int(meta.get("support_count", 0)) + 1
        meta["last_observed_at"] = now
        if not meta.get("title"):
            meta["title"] = title

        # students_count: keep an internal hashed set so we don't store names.
        # We use a hash to satisfy the anonymization rule (no raw names in frontmatter).
        if new_student_name:
            import hashlib
            seen_hashes = set(meta.get("_student_hashes", []))
            h = hashlib.sha256(new_student_name.encode("utf-8")).hexdigest()[:16]
            if h not in seen_hashes:
                seen_hashes.add(h)
                meta["_student_hashes"] = sorted(seen_hashes)
                meta["students_count"] = len(seen_hashes)

        # Append anonymized evidence. The lint runs over the FINAL content before write.
        body = body.rstrip() + f"\n- {new_evidence.strip()}\n"

        post = frontmatter.Post(content=body, **{k: v for k, v in meta.items()})
        full_text = frontmatter.dumps(post)

        # Lint AFTER strip of internal fields representation isn't ideal — we lint the body only,
        # since frontmatter contains the hash list that doesn't reveal names. Body must be clean.
        assert_clean(body, file_path=path)

        path.write_text(full_text + ("\n" if not full_text.endswith("\n") else ""), encoding="utf-8")

        return {
            "path": str(path.relative_to(WIKI_ROOT)),
            "support_count": meta["support_count"],
            "students_count": meta["students_count"],
            "created": not path.exists(),
        }
```

- [ ] **Step 2: Verify create + update**

```bash
python3 -c "
from intelligence.api.services.wiki_writer import upsert_behavioral_node
r1 = upsert_behavioral_node('antecedents', 'peer-takes-material', 'Peer takes material', 'A peer reaches for the material the focal child is carrying or working with.', 'a peer reaches for the cylinder mid-carry', new_student_name='Mira Shah')
r2 = upsert_behavioral_node('antecedents', 'peer-takes-material', 'Peer takes material', '', 'a peer reaches for a chosen practical-life material', new_student_name='Arjun Nair')
print(r1, r2)
"
cat wiki/behavioral/antecedents/peer-takes-material.md
```
Expected: file exists with `support_count: 2`, `students_count: 2`, two evidence bullets, `_student_hashes: [...]` with 2 hashes (no raw names).

- [ ] **Step 3: Verify anonymization lint catches a leak**

```bash
python3 -c "
from intelligence.api.services.wiki_writer import upsert_behavioral_node
try:
    upsert_behavioral_node('antecedents', 'peer-takes-material', 'X', '', 'Mira reaches for the cylinder', new_student_name='Mira Shah')
    print('FAIL — leak was not caught')
except Exception as e:
    print('OK — caught:', type(e).__name__)
"
```
Expected: `OK — caught: AnonymizationLeak`.

- [ ] **Step 4: Clean up the test artifact**

```bash
rm wiki/behavioral/antecedents/peer-takes-material.md
```

- [ ] **Step 5: Commit**

```bash
git add intelligence/api/services/wiki_writer.py
git commit -m "phase2: implement upsert_behavioral_node with anonymization lint and student-hash counting

students_count tracks unique students via SHA256 hashes stored in frontmatter
field _student_hashes — names never appear in behavioral pages.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.3: Implement `wiki_writer.upsert_behavioral_edge`

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py`

- [ ] **Step 1: Replace the `upsert_behavioral_edge` stub**

```python
from intelligence.api.services.wiki_paths import behavioral_edge_path


def upsert_behavioral_edge(
    src_type: str,
    src_slug: str,
    rel: str,
    dst_type: str,
    dst_slug: str,
    new_evidence: str,
    new_student_name: str | None = None,
) -> dict:
    with _WRITE_LOCK:
        path = behavioral_edge_path(src_type, src_slug, rel, dst_type, dst_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        if path.exists():
            post = frontmatter.load(path)
            meta = post.metadata
            body = post.content
        else:
            meta = {
                "src_slug": f"{src_type}/{src_slug}",
                "rel": rel,
                "dst_slug": f"{dst_type}/{dst_slug}",
                "support_count": 0,
                "students_count": 0,
                "first_observed_at": now,
                "last_observed_at": None,
            }
            body = (
                f"# {src_type}/{src_slug} —[{rel}]→ {dst_type}/{dst_slug}\n\n"
                f"## Evidence\n\n"
            )

        meta["support_count"] = int(meta.get("support_count", 0)) + 1
        meta["last_observed_at"] = now

        if new_student_name:
            import hashlib
            hashes = set(meta.get("_student_hashes", []))
            h = hashlib.sha256(new_student_name.encode("utf-8")).hexdigest()[:16]
            if h not in hashes:
                hashes.add(h)
                meta["_student_hashes"] = sorted(hashes)
                meta["students_count"] = len(hashes)

        body = body.rstrip() + f"\n- {new_evidence.strip()}\n"

        post = frontmatter.Post(content=body, **{k: v for k, v in meta.items()})
        full_text = frontmatter.dumps(post)
        assert_clean(body, file_path=path)
        path.write_text(full_text + ("\n" if not full_text.endswith("\n") else ""), encoding="utf-8")

        return {
            "path": str(path.relative_to(WIKI_ROOT)),
            "support_count": meta["support_count"],
            "students_count": meta["students_count"],
        }
```

- [ ] **Step 2: Smoke**

```bash
python3 -c "
from intelligence.api.services.wiki_writer import upsert_behavioral_edge
r = upsert_behavioral_edge('antecedents', 'peer-takes-material', 'triggers', 'behaviors', 'drops-and-flees', 'peer takes material → child drops it and runs to the reading corner', new_student_name='Mira Shah')
print(r)
"
ls wiki/behavioral/_edges/
```
Expected: file `antecedents--peer-takes-material--triggers--behaviors--drops-and-flees.md` exists.

- [ ] **Step 3: Cleanup + commit**

```bash
rm wiki/behavioral/_edges/antecedents--peer-takes-material--triggers--behaviors--drops-and-flees.md
git add intelligence/api/services/wiki_writer.py
git commit -m "phase2: implement upsert_behavioral_edge with anonymization lint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.4: Implement `wiki_writer.write_incident` and `update_student_rollups`

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py`

- [ ] **Step 1: Add helpers and `write_incident`**

Append to `wiki_writer.py`:
```python
from intelligence.api.services.wiki_paths import incident_path, student_dir


def write_incident(
    student_name: str,
    note_id: int,
    severity: str,
    note_body: str,
    interpretation: str,
    behavioral_refs: list[str],
    peers_present: list[str],
    educator: str,
    ingested_at_iso: str,
    slug_hint: str,
) -> str:
    """Write one student incident page. Returns the file path written (relative to wiki/)."""
    with _WRITE_LOCK:
        from intelligence.api.services.wiki_paths import slugify
        slug = slugify(slug_hint)[:60] or f"note-{note_id}"
        path = incident_path(student_name, ingested_at_iso, slug)
        path.parent.mkdir(parents=True, exist_ok=True)

        meta = {
            "student": student_name,
            "note_id": note_id,
            "severity": severity,
            "behavioral_refs": behavioral_refs,
            "peers_present": peers_present,
            "educator": educator,
            "ingested_at": ingested_at_iso,
        }
        body = f"## Note\n\n{note_body.strip()}\n\n## Interpretation\n\n{interpretation.strip()}\n"
        post = frontmatter.Post(content=body, **{k: v for k, v in meta.items()})
        path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
        return str(path.relative_to(WIKI_ROOT))


def update_student_rollups(student_name: str) -> None:
    """Refresh profile.md, timeline.md, patterns.md, protective_factors.md, relationships.md."""
    with _WRITE_LOCK:
        sdir = student_dir(student_name)
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "incidents").mkdir(parents=True, exist_ok=True)

        incidents = sorted((sdir / "incidents").glob("*.md"))

        # Profile rollup
        from intelligence.api.services.ghost_client import get_student_profile
        profile = get_student_profile(student_name) or {}
        profile_md = (
            f"---\nstudent: {student_name}\nincident_count: {len(incidents)}\n"
            f"current_severity: {profile.get('current_severity', 'unknown')}\n"
            f"trend: {profile.get('trend', 'unknown')}\n---\n\n"
            f"# {student_name}\n\n"
            f"## Latest summary\n\n{profile.get('latest_summary', '_(no observations yet)_')}\n\n"
            f"## Patterns\n\n{profile.get('latest_patterns', '_(no observations yet)_')}\n\n"
            f"## Latest suggestions\n\n{profile.get('latest_suggestions', '_(no observations yet)_')}\n"
        )
        (sdir / "profile.md").write_text(profile_md, encoding="utf-8")

        # Timeline rollup
        timeline_lines = ["# Timeline\n\n"]
        for inc in incidents:
            try:
                post = frontmatter.load(inc)
                ts = post.metadata.get("ingested_at", "?")
                sev = post.metadata.get("severity", "?")
                timeline_lines.append(f"- [{ts}] ({sev}) [{inc.stem}](incidents/{inc.name})\n")
            except Exception:
                continue
        (sdir / "timeline.md").write_text("".join(timeline_lines), encoding="utf-8")

        # Patterns rollup — derived from behavioral_refs frequencies
        from collections import Counter
        ref_counter: Counter = Counter()
        for inc in incidents:
            try:
                post = frontmatter.load(inc)
                for ref in post.metadata.get("behavioral_refs", []) or []:
                    ref_counter[ref] += 1
            except Exception:
                continue
        patterns_lines = ["# Per-student patterns\n\n", "Behavioral references ranked by frequency.\n\n"]
        for ref, count in ref_counter.most_common():
            patterns_lines.append(f"- [{ref}](../../{ref}.md) — {count} occurrence(s)\n")
        (sdir / "patterns.md").write_text("".join(patterns_lines), encoding="utf-8")

        # Protective factors stub (Phase 5 may enrich)
        (sdir / "protective_factors.md").write_text(
            f"# {student_name} — Protective Factors\n\n_(populated as the agent identifies DECA-style strengths)_\n",
            encoding="utf-8",
        )

        # Relationships rollup — peers seen in this student's incident frontmatter
        peer_counter: Counter = Counter()
        edu_counter: Counter = Counter()
        for inc in incidents:
            try:
                post = frontmatter.load(inc)
                for peer in post.metadata.get("peers_present", []) or []:
                    peer_counter[peer] += 1
                edu = post.metadata.get("educator")
                if edu:
                    edu_counter[edu] += 1
            except Exception:
                continue
        rel_lines = [f"# {student_name} — Relationships\n\n", "## Peers (from incident notes)\n\n"]
        for peer, c in peer_counter.most_common():
            rel_lines.append(f"- {peer} — {c} co-occurrence(s)\n")
        rel_lines.append("\n## Educators\n\n")
        for edu, c in edu_counter.most_common():
            rel_lines.append(f"- {edu} — {c} observation(s)\n")
        (sdir / "relationships.md").write_text("".join(rel_lines), encoding="utf-8")
```

- [ ] **Step 2: Smoke test**

```bash
python3 -c "
from datetime import datetime, timezone
from intelligence.api.services.wiki_writer import write_incident, update_student_rollups
ts = datetime.now(timezone.utc).isoformat()
p = write_incident(
    student_name='Mira Shah',
    note_id=999,
    severity='yellow',
    note_body='Mira chose the pink tower and worked carefully for several minutes before a peer reached for the cylinder she was carrying. She dropped the material and ran to the reading corner.',
    interpretation='Likely escape function; emotional brain state after peer took material.',
    behavioral_refs=['behavioral/antecedents/peer-takes-material', 'behavioral/behaviors/drops-and-flees', 'behavioral/functions/escape'],
    peers_present=['Arjun Nair'],
    educator='Sajitha Kandathil',
    ingested_at_iso=ts,
    slug_hint='peer takes cylinder',
)
print('wrote', p)
update_student_rollups('Mira Shah')
print('rollups updated')
"
ls wiki/students/Mira_Shah/incidents/
cat wiki/students/Mira_Shah/profile.md
```
Expected: incident file exists; profile.md and other rollups exist.

- [ ] **Step 3: Cleanup + commit**

```bash
rm -f wiki/students/Mira_Shah/incidents/*.md
git checkout -- wiki/students/Mira_Shah/.gitkeep 2>/dev/null || true
git add intelligence/api/services/wiki_writer.py
git commit -m "phase2: implement write_incident and update_student_rollups

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.5: Implement `wiki_indexer` (incremental + full rebuild)

**Files:**
- Modify: `intelligence/api/services/wiki_indexer.py`

- [ ] **Step 1: Replace stubs**

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import psycopg2.extras

from intelligence.api.services.ghost_client import _connect_agent_db
from intelligence.api.services.wiki_paths import WIKI_ROOT


def _file_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def index_behavioral_node(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    summary = ""
    if "## Summary" in post.content:
        summary = post.content.split("## Summary", 1)[1].split("##", 1)[0].strip()

    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO behavioral_nodes (
                    slug, type, title, summary,
                    support_count, students_count, literature_refs,
                    curiosity_score, curiosity_factors,
                    last_observed_at, last_research_fetched_at, created_at,
                    file_path, file_mtime
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (slug) DO UPDATE SET
                    type = EXCLUDED.type,
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    support_count = EXCLUDED.support_count,
                    students_count = EXCLUDED.students_count,
                    literature_refs = EXCLUDED.literature_refs,
                    curiosity_score = EXCLUDED.curiosity_score,
                    curiosity_factors = EXCLUDED.curiosity_factors,
                    last_observed_at = EXCLUDED.last_observed_at,
                    last_research_fetched_at = EXCLUDED.last_research_fetched_at,
                    file_path = EXCLUDED.file_path,
                    file_mtime = EXCLUDED.file_mtime
                """,
                (
                    meta.get("slug"),
                    meta.get("type"),
                    meta.get("title", ""),
                    summary,
                    int(meta.get("support_count", 0)),
                    int(meta.get("students_count", 0)),
                    int(meta.get("literature_refs", 0)),
                    float(meta.get("curiosity_score", 0.0)),
                    psycopg2.extras.Json(meta.get("last_curiosity_factors", {})),
                    meta.get("last_observed_at"),
                    meta.get("last_research_fetched_at"),
                    meta.get("created_at"),
                    str(file_path.relative_to(WIKI_ROOT)),
                    _file_mtime(file_path),
                ),
            )
            conn.commit()


def index_behavioral_edge(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    src_full = meta.get("src_slug", "")
    dst_full = meta.get("dst_slug", "")

    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO behavioral_edges (
                    src_slug, rel, dst_slug,
                    support_count, students_count,
                    first_observed_at, last_observed_at,
                    file_path
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (src_slug, rel, dst_slug) DO UPDATE SET
                    support_count = EXCLUDED.support_count,
                    students_count = EXCLUDED.students_count,
                    last_observed_at = EXCLUDED.last_observed_at,
                    file_path = EXCLUDED.file_path
                """,
                (
                    src_full, meta.get("rel"), dst_full,
                    int(meta.get("support_count", 0)),
                    int(meta.get("students_count", 0)),
                    meta.get("first_observed_at"),
                    meta.get("last_observed_at"),
                    str(file_path.relative_to(WIKI_ROOT)),
                ),
            )
            conn.commit()


def index_student_incident(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    refs = list(meta.get("behavioral_refs", []) or [])

    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO student_incidents (
                    student_name, note_id, severity, ingested_at,
                    file_path, file_mtime, behavioral_ref_slugs
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    meta.get("student"),
                    meta.get("note_id"),
                    meta.get("severity"),
                    meta.get("ingested_at"),
                    str(file_path.relative_to(WIKI_ROOT)),
                    _file_mtime(file_path),
                    refs,
                ),
            )
            conn.commit()


def index_student_profile(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    student = meta.get("student")
    if not student:
        return

    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO student_profiles_index (
                    student_name, current_severity, trend,
                    incident_count, patterns_summary, file_path, file_mtime
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (student_name) DO UPDATE SET
                    current_severity = EXCLUDED.current_severity,
                    trend = EXCLUDED.trend,
                    incident_count = EXCLUDED.incident_count,
                    patterns_summary = EXCLUDED.patterns_summary,
                    file_path = EXCLUDED.file_path,
                    file_mtime = EXCLUDED.file_mtime
                """,
                (
                    student,
                    meta.get("current_severity"),
                    meta.get("trend"),
                    int(meta.get("incident_count", 0)),
                    post.content[:500],
                    str(file_path.relative_to(WIKI_ROOT)),
                    _file_mtime(file_path),
                ),
            )
            conn.commit()


def full_rebuild() -> dict[str, int]:
    counts = {"nodes": 0, "edges": 0, "incidents": 0, "profiles": 0}
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE behavioral_nodes, behavioral_edges, student_incidents, student_profiles_index")
            conn.commit()

    behavioral = WIKI_ROOT / "behavioral"
    for ntype_dir in [d for d in behavioral.iterdir() if d.is_dir() and not d.name.startswith("_")]:
        for f in ntype_dir.glob("*.md"):
            index_behavioral_node(f)
            counts["nodes"] += 1
    edges_dir = behavioral / "_edges"
    if edges_dir.exists():
        for f in edges_dir.glob("*.md"):
            index_behavioral_edge(f)
            counts["edges"] += 1

    students = WIKI_ROOT / "students"
    for sdir in [d for d in students.iterdir() if d.is_dir()]:
        profile = sdir / "profile.md"
        if profile.exists():
            index_student_profile(profile)
            counts["profiles"] += 1
        inc_dir = sdir / "incidents"
        if inc_dir.exists():
            for f in inc_dir.glob("*.md"):
                index_student_incident(f)
                counts["incidents"] += 1

    return counts
```

- [ ] **Step 2: Wire writer to indexer**

In `wiki_writer.py`, add at the top after the existing imports:
```python
from intelligence.api.services import wiki_indexer
```

And add a helper to call after each writer:
```python
def _index_after_write(path: Path, kind: str) -> None:
    """Sync the just-written file into Postgres."""
    try:
        if kind == "behavioral_node":
            wiki_indexer.index_behavioral_node(path)
        elif kind == "behavioral_edge":
            wiki_indexer.index_behavioral_edge(path)
        elif kind == "incident":
            wiki_indexer.index_student_incident(path)
        elif kind == "profile":
            wiki_indexer.index_student_profile(path)
    except Exception as e:
        # Index drift is recoverable via /api/wiki/reindex; don't crash the writer.
        import sys
        print(f"[wiki_writer] index sync failed for {path}: {e}", file=sys.stderr, flush=True)
```

Then add `_index_after_write(path, "behavioral_node")` at the end of `upsert_behavioral_node`, `_index_after_write(path, "behavioral_edge")` at the end of `upsert_behavioral_edge`, `_index_after_write(path, "incident")` at the end of `write_incident`, and `_index_after_write(sdir / "profile.md", "profile")` at the end of `update_student_rollups`.

- [ ] **Step 3: Verify full rebuild round-trip**

```bash
python3 -c "
from intelligence.api.services.wiki_indexer import full_rebuild
print(full_rebuild())
"
curl -s http://localhost:8000/api/wiki/reindex -X POST | jq .
```
Expected: `{'nodes': 0, 'edges': 0, 'incidents': 0, 'profiles': 0}` (empty wiki) and HTTP 200.

- [ ] **Step 4: Commit**

```bash
git add intelligence/api/services/wiki_indexer.py intelligence/api/services/wiki_writer.py
git commit -m "phase2: implement wiki_indexer (incremental + full rebuild) and wire writer to it

Each writer call syncs the resulting file to Postgres. Index failures are
logged but non-fatal; full rebuild via POST /api/wiki/reindex recovers drift.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.6: Wire `self_improve.py` to call wiki_writer

**Files:**
- Modify: `intelligence/api/services/self_improve.py`

- [ ] **Step 1: Inspect current cumulative-reassessment path**

Run: `grep -n "def run_agent_cycle\|def reassess\|insert_snapshot\|upsert_student_profile" intelligence/api/services/self_improve.py`

Find the function that, after the LLM produces an assessment for a student's note, currently writes to `profile_snapshots` and `student_profiles`. That call site is the integration point.

- [ ] **Step 2: After legacy DB writes, also call wiki_writer**

After the existing `insert_snapshot(...)` and `upsert_student_profile(...)` lines in the per-note loop, add:

```python
from intelligence.api.services import wiki_writer
from datetime import datetime, timezone

# Build the behavioral_refs from the LLM assessment.
# Expects assessment dict to include 'behavioral_nodes': list of {type, slug, title, summary, evidence}
# and 'behavioral_edges': list of {src_type, src_slug, rel, dst_type, dst_slug, evidence}.
# If your assessment dict doesn't yet produce these fields, this block is a no-op until
# llm_service.assess_note returns them — see Task 2.7 below.

assessment_nodes = assessment.get("behavioral_nodes") or []
assessment_edges = assessment.get("behavioral_edges") or []

ref_paths: list[str] = []
for n in assessment_nodes:
    try:
        wiki_writer.upsert_behavioral_node(
            node_type=n["type"],
            slug=n["slug"],
            title=n.get("title", n["slug"].replace("-", " ").title()),
            summary=n.get("summary", ""),
            new_evidence=n["evidence"],
            new_student_name=student_name,
        )
        ref_paths.append(f"behavioral/{n['type']}/{n['slug']}")
    except Exception as e:
        import sys
        print(f"[self_improve] node upsert failed: {e}", file=sys.stderr, flush=True)

for e in assessment_edges:
    try:
        wiki_writer.upsert_behavioral_edge(
            src_type=e["src_type"],
            src_slug=e["src_slug"],
            rel=e["rel"],
            dst_type=e["dst_type"],
            dst_slug=e["dst_slug"],
            new_evidence=e["evidence"],
            new_student_name=student_name,
        )
    except Exception as ex:
        import sys
        print(f"[self_improve] edge upsert failed: {ex}", file=sys.stderr, flush=True)

# Write the incident page itself.
ingested_at = datetime.now(timezone.utc).isoformat()
try:
    wiki_writer.write_incident(
        student_name=student_name,
        note_id=note["id"],
        severity=assessment.get("severity", "yellow"),
        note_body=note["body"],
        interpretation=assessment.get("profile_summary", ""),
        behavioral_refs=ref_paths,
        peers_present=assessment.get("peers_present", []) or [],
        educator=assessment.get("educator", "") or "",
        ingested_at_iso=ingested_at,
        slug_hint=assessment.get("slug_hint", f"note-{note['id']}"),
    )
    wiki_writer.update_student_rollups(student_name)
    wiki_writer.update_indexes()
    wiki_writer.append_log("incident_written", f"{student_name} note #{note['id']}", student_name=student_name)
except Exception as ex:
    import sys
    print(f"[self_improve] wiki write failed: {ex}", file=sys.stderr, flush=True)
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile intelligence/api/services/self_improve.py`
Expected: exit 0.

- [ ] **Step 4: Commit (Task 2.7 will fix the LLM service to actually produce the new fields)**

```bash
git add intelligence/api/services/self_improve.py
git commit -m "phase2: wire self_improve to wiki_writer for incidents/nodes/edges/rollups

Behavioral node/edge upserts are no-ops until llm_service.assess_note
returns 'behavioral_nodes' and 'behavioral_edges' (Task 2.7).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.7: Extend `llm_service.assess_note` to emit behavioral nodes/edges

**Files:**
- Modify: `intelligence/api/services/llm_service.py`

- [ ] **Step 1: Locate `assess_note`**

Run: `grep -n "def assess_note\|response_format" intelligence/api/services/llm_service.py`

- [ ] **Step 2: Update the system prompt + JSON schema to include behavioral decomposition**

Modify the `assess_note` prompt to instruct the LLM to also return `behavioral_nodes` and `behavioral_edges` arrays. Append to the existing system prompt:

```text
After your assessment, decompose this observation into a behavioral knowledge graph using the ABC + SEAT + BrainState taxonomy. Return a `behavioral_nodes` array and a `behavioral_edges` array in the JSON.

Allowed node types (use these exact strings): "setting_events", "antecedents", "behaviors", "functions", "brain_states", "responses", "protective_factors".

Allowed edge relations (use these exact strings): "predisposes", "amplifies", "triggers", "serves", "occurs_in", "gates", "follows", "reinforces", "extinguishes", "co-regulates", "evidences", "undermines", "recurs_with".

For each node, return: {"type": <node_type>, "slug": <kebab-case>, "title": <short title>, "summary": <one-sentence anonymized definition>, "evidence": <one anonymized sentence about THIS observation, no names, no dates, no times, no ages above "3-4" / "4-5" bands>}.

For each edge, return: {"src_type": ..., "src_slug": ..., "rel": ..., "dst_type": ..., "dst_slug": ..., "evidence": <anonymized one-liner>}.

CRITICAL: evidence strings MUST NOT contain student names, educator names, peer names, dates, or specific times. Phrasing like "a 3-4 year old", "a peer", "the guide" is required. The behavioral graph is anonymized; violations will be rejected by an automated lint.

Also include in the JSON: `peers_present` (array of student names from the observation), `educator` (educator name if present), and `slug_hint` (a 2-4 word slug describing this incident).
```

Update the JSON schema/example in the prompt to show these new fields. The function should already do `json.loads(response.choices[0].message.content)`; the new fields will flow through automatically.

- [ ] **Step 3: Syntax check + smoke**

```bash
python3 -m py_compile intelligence/api/services/llm_service.py
python3 -c "
from intelligence.api.services.llm_service import assess_note
r = assess_note('Mira Shah', 'Mira chose the pink tower and worked carefully for several minutes before a peer reached for the cylinder she was carrying. She dropped the material and ran to the reading corner.')
import json; print(json.dumps(r, indent=2)[:1500])
"
```
Expected: JSON includes `behavioral_nodes` and `behavioral_edges` arrays with anonymized evidence strings.

- [ ] **Step 4: End-to-end run**

Boot the API, start the streamer, watch the wiki populate:
```bash
uvicorn intelligence.api.main:app --port 8000 &
sleep 1
python3 -m notes_streamer.streamer &
STREAM_PID=$!
sleep 30
kill $STREAM_PID
```
Then:
```bash
ls wiki/students/Mira_Shah/incidents/ | head -3
ls wiki/behavioral/antecedents/ | head -5
ls wiki/behavioral/_edges/ | head -5
python3 -m scripts.lint_anonymization || echo "ANON LEAK"   # script defined in Task 2.8
```
Expected: incident files appear under each persona's `incidents/`; behavioral nodes appear under their type folders; no anonymization leaks.

- [ ] **Step 5: Commit**

```bash
git add intelligence/api/services/llm_service.py
git commit -m "phase2: extend assess_note to return behavioral_nodes and behavioral_edges arrays

Anonymization rules included in the prompt; downstream lint enforces them
on every wiki write.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.8: CLI anonymization linter for the whole wiki

**Files:**
- Create: `scripts/lint_anonymization.py`

- [ ] **Step 1: Write the linter**

```python
"""Walk wiki/behavioral/** and assert no anonymization leaks. Exit non-zero on violation."""
from __future__ import annotations

import sys
from pathlib import Path

from intelligence.api.services.anonymization_lint import scan
from intelligence.api.services.wiki_paths import WIKI_ROOT


def main() -> int:
    failures = 0
    behavioral_root = WIKI_ROOT / "behavioral"
    for path in behavioral_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        violations = scan(text)
        if violations:
            failures += 1
            print(f"[LEAK] {path.relative_to(WIKI_ROOT)}")
            for v in violations:
                print(f"   - {v.kind}: '{v.match}' (...{v.snippet}...)")
    if failures:
        print(f"\nFAILED — {failures} files leaked.")
        return 1
    print("OK — no anonymization leaks under wiki/behavioral/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run**

```bash
python3 -m scripts.lint_anonymization
```
Expected: `OK — no anonymization leaks under wiki/behavioral/`. Exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/lint_anonymization.py
git commit -m "phase2: add scripts/lint_anonymization.py CLI linter

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

**End of Phase 2.** Wiki is the source of truth; Postgres index is in sync; anonymization is enforced. Phase 3 unblocks.

---

## Phase 3 — Curiosity gate (depends on Phase 2)

Goal: every behavioral node carries a `curiosity_score`, recomputed on every touch. When score crosses 0.70 (and cooldown elapsed), `kg_agent` fires research and writes an OpenAlex paper page.

### Task 3.1: Implement `curiosity.compute_factors`

**Files:**
- Modify: `intelligence/api/services/curiosity.py`

- [ ] **Step 1: Replace the `compute_factors` stub**

```python
import math
from datetime import datetime, timezone

import frontmatter

from intelligence.api.services.wiki_paths import WIKI_ROOT, BEHAVIORAL_TYPES
from intelligence.api.services.ghost_client import _connect_agent_db


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _find_node_path(slug: str):
    """slug may be 'antecedents/peer-takes-material' or just 'peer-takes-material'."""
    if "/" in slug:
        ntype, name = slug.split("/", 1)
        candidate = WIKI_ROOT / "behavioral" / ntype / f"{name}.md"
        return candidate if candidate.exists() else None
    for ntype in BEHAVIORAL_TYPES:
        candidate = WIKI_ROOT / "behavioral" / ntype / f"{slug}.md"
        if candidate.exists():
            return candidate
    return None


def _recent_severity_for_node(slug_full: str) -> float:
    """Return max severity (red=1.0, yellow=0.5, green=0.0) of recent incidents touching this node."""
    sev_map = {"red": 1.0, "yellow": 0.5, "green": 0.0}
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT severity FROM student_incidents "
                "WHERE %s = ANY(behavioral_ref_slugs) "
                "ORDER BY ingested_at DESC LIMIT 5",
                (f"behavioral/{slug_full}",),
            )
            rows = cur.fetchall()
    return max((sev_map.get(r[0], 0.0) for r in rows), default=0.0)


def compute_factors(node_slug: str, recent_evidence_text: str | None = None) -> CuriosityFactors:
    """Compute all 6 factors for a behavioral node, given its current wiki state."""
    path = _find_node_path(node_slug)
    if path is None:
        # Unknown node — minimal defaults
        return CuriosityFactors(
            novelty=1.0, recurrence_gap=0.0, cross_student=0.0,
            surprise=0.0, severity_weight=0.0, recency=0.0,
        )

    post = frontmatter.load(path)
    meta = post.metadata
    support_count = int(meta.get("support_count", 0))
    students_count = int(meta.get("students_count", 0))
    literature_refs = int(meta.get("literature_refs", 0))

    novelty = 1.0 / (1.0 + literature_refs)
    recurrence_gap = _sigmoid(support_count - 3.0 * literature_refs)
    cross_student = _sigmoid(students_count - 2.0)
    # +0.20 first-crossing-of-3 bump, decayed back over 6 hours
    if students_count == 3 and meta.get("_first_crossed_3_at") is None:
        meta["_first_crossed_3_at"] = datetime.now(timezone.utc).isoformat()
        # Persist this stamp on next write — we don't write here directly.
        cross_student = min(1.0, cross_student + 0.20)
    elif meta.get("_first_crossed_3_at"):
        try:
            t0 = datetime.fromisoformat(meta["_first_crossed_3_at"])
            hours = (datetime.now(timezone.utc) - t0).total_seconds() / 3600.0
            bump = max(0.0, 0.20 * math.exp(-hours / 6.0))
            cross_student = min(1.0, cross_student + bump)
        except Exception:
            pass

    # Surprise: simple heuristic — token-overlap distance between new evidence and existing summary
    surprise = 0.0
    if recent_evidence_text:
        existing_summary = ""
        if "## Summary" in post.content:
            existing_summary = post.content.split("## Summary", 1)[1].split("##", 1)[0].lower()
        new_tokens = set(recent_evidence_text.lower().split())
        old_tokens = set(existing_summary.split())
        if new_tokens:
            shared = len(new_tokens & old_tokens) / len(new_tokens)
            surprise = max(0.0, 1.0 - shared)

    severity_weight = _recent_severity_for_node(
        f"{meta.get('type', '').rstrip('s') or 'node'}s/{meta.get('slug')}"
        if meta.get("type") and not meta["type"].endswith("s")
        else f"{meta.get('type')}/{meta.get('slug')}"
    )

    last_obs = meta.get("last_observed_at")
    recency = 0.0
    if last_obs:
        try:
            t = datetime.fromisoformat(last_obs)
            hours = (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
            recency = math.exp(-hours / 24.0)
        except Exception:
            pass

    return CuriosityFactors(
        novelty=round(novelty, 3),
        recurrence_gap=round(recurrence_gap, 3),
        cross_student=round(cross_student, 3),
        surprise=round(surprise, 3),
        severity_weight=round(severity_weight, 3),
        recency=round(recency, 3),
    )
```

- [ ] **Step 2: Smoke**

```bash
python3 -c "
from intelligence.api.services.curiosity import compute_factors
f = compute_factors('peer-takes-material', recent_evidence_text='peer takes the chosen material; child screams')
print(f.to_dict(), '->', round(f.score(), 3))
"
```
Expected: dict with six numeric factors and a score in `[0, 1]`.

- [ ] **Step 3: Commit**

```bash
git add intelligence/api/services/curiosity.py
git commit -m "phase3: implement curiosity.compute_factors with 6-signal formula

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.2: Implement `curiosity.evaluate_gate` with cooldown + persistence

**Files:**
- Modify: `intelligence/api/services/curiosity.py`

- [ ] **Step 1: Replace the `evaluate_gate` stub**

```python
from datetime import timedelta

import psycopg2.extras
from intelligence.api.services.ghost_client import (
    _connect_agent_db,
    get_runtime_overrides,
)


def _current_weights() -> dict[str, float]:
    overrides = get_runtime_overrides()
    custom = overrides.get("_curiosity_weights") or {}
    weights = dict(DEFAULT_WEIGHTS)
    for k, v in custom.items():
        if k in weights and isinstance(v, (int, float)):
            weights[k] = float(v)
    return weights


def _last_research_at(node_slug: str):
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT last_research_fetched_at FROM behavioral_nodes WHERE slug = %s",
                (node_slug.split("/")[-1],),
            )
            row = cur.fetchone()
            return row[0] if row else None


def evaluate_gate(node_slug: str) -> dict:
    """Return {fire: bool, score: float, factors: dict, reason: str}."""
    factors = compute_factors(node_slug)
    weights = _current_weights()
    score = factors.score(weights)

    last = _last_research_at(node_slug)
    cooldown_active = False
    if last:
        elapsed = datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)
        cooldown_active = elapsed < timedelta(minutes=COOLDOWN_MINUTES)

    fire = (score >= CURIOSITY_THRESHOLD) and (not cooldown_active)
    reason = (
        "score below threshold" if score < CURIOSITY_THRESHOLD
        else "cooldown active" if cooldown_active
        else "fire"
    )

    # Persist event row for the audit log surfaced in /console.
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO curiosity_events (node_slug, fired_at, curiosity_score, factors, "
                "triggered_research, paper_count) VALUES (%s, NOW(), %s, %s, %s, 0)",
                (node_slug, score, psycopg2.extras.Json(factors.to_dict()), fire),
            )
            conn.commit()

    return {"fire": fire, "score": round(score, 3), "factors": factors.to_dict(), "reason": reason, "weights": weights}
```

- [ ] **Step 2: Smoke**

```bash
curl -s -X POST http://localhost:8000/api/curiosity/recompute/peer-takes-material | jq .
curl -s -X POST http://localhost:8000/api/curiosity/investigate/peer-takes-material | jq .
curl -s http://localhost:8000/api/curiosity/events | jq '.events | length'
```
Expected: recompute returns factors + score; investigate returns gate decision; events list grows by 1.

- [ ] **Step 3: Commit**

```bash
git add intelligence/api/services/curiosity.py
git commit -m "phase3: implement curiosity.evaluate_gate with 30-min cooldown and event persistence

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.3: Wire `kg_agent` to use curiosity gate as third trigger

**Files:**
- Modify: `intelligence/api/services/kg_agent.py`

- [ ] **Step 1: In `enrich_student_knowledge`, evaluate curiosity for each touched behavioral node**

Locate `enrich_student_knowledge`. After the existing "thin patterns" + "emergency" trigger checks, add a third path that fires when any behavioral node touched by this student's recent assessment has `evaluate_gate(...).fire == True`. Pseudocode:

```python
from intelligence.api.services.curiosity import evaluate_gate

def _curious_nodes_for_assessment(assessment: dict) -> list[str]:
    """Return slugs of behavioral nodes whose curiosity gate fires."""
    nodes = assessment.get("behavioral_nodes") or []
    fired: list[str] = []
    for n in nodes:
        slug_full = f"{n['type']}/{n['slug']}"
        result = evaluate_gate(slug_full)
        if result["fire"]:
            fired.append(slug_full)
    return fired
```

In the existing decision branch where the function decides whether to fetch from OpenAlex, change the condition from "thin patterns OR emergency" to "thin patterns OR emergency OR curious_nodes is non-empty". When the curiosity branch fires, log the trigger reason and prepend the curious node slugs as additional search-query seed terms.

After successful OpenAlex fetch and storage, update `behavioral_nodes.last_research_fetched_at` for each fired node and increment `literature_refs`:

```python
from intelligence.api.services.ghost_client import _connect_agent_db

def _mark_node_researched(slug_full: str, paper_count: int) -> None:
    slug = slug_full.split("/")[-1]
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE behavioral_nodes SET last_research_fetched_at = NOW(), "
                "literature_refs = literature_refs + %s WHERE slug = %s",
                (paper_count, slug),
            )
            cur.execute(
                "UPDATE curiosity_events SET paper_count = %s "
                "WHERE node_slug = %s AND fired_at = (SELECT MAX(fired_at) FROM curiosity_events WHERE node_slug = %s)",
                (paper_count, slug_full, slug_full),
            )
            conn.commit()
```

- [ ] **Step 2: Write paper pages to `wiki/sources/openalex/`**

In `_store_openalex_result`, after the existing `insert_literature(...)` and `upsert_knowledge_graph_entry(...)` calls, also write a markdown page:

```python
from intelligence.api.services.wiki_paths import source_paper_path
import frontmatter as _fm

def _write_paper_page(meta: dict, abstract: str, summary: dict, query: str, student_name: str | None) -> str:
    path = source_paper_path(meta.get("openalex_id", "unknown"))
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_meta = {
        "openalex_id": meta.get("openalex_id"),
        "title": meta.get("title"),
        "authors": meta.get("authors", []),
        "publication_year": meta.get("publication_year"),
        "cited_by_count": meta.get("cited_by_count", 0),
        "landing_page_url": meta.get("landing_page_url"),
        "fetched_for_query": query,
        "fetched_for_student": student_name,
    }
    body = (
        f"# {meta.get('title')}\n\n"
        f"## Relevance\n\n{summary.get('relevance', '')}\n\n"
        f"## Abstract\n\n{(abstract or '')[:2000]}\n\n"
        f"## Insights\n\n" + "\n".join(f"- {i}" for i in (summary.get('insights') or [])) + "\n"
    )
    post = _fm.Post(content=body, **fm_meta)
    path.write_text(_fm.dumps(post) + "\n", encoding="utf-8")
    return str(path)
```

Call `_write_paper_page(meta, abstract, summary, query, student_name)` after the existing storage calls.

If `student_name` is set, also append a link to that student's `literature.md`:
```python
from intelligence.api.services.wiki_paths import student_dir

def _link_paper_to_student(student_name: str, paper_meta: dict) -> None:
    sdir = student_dir(student_name)
    sdir.mkdir(parents=True, exist_ok=True)
    lit = sdir / "literature.md"
    line = f"- [{paper_meta.get('title')}](../../sources/openalex/{paper_meta.get('openalex_id', '').split('/')[-1]}.md) — {paper_meta.get('publication_year')}\n"
    if not lit.exists():
        lit.write_text(f"# {student_name} — Research Literature\n\n", encoding="utf-8")
    with lit.open("a", encoding="utf-8") as f:
        f.write(line)
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile intelligence/api/services/kg_agent.py`
Expected: exit 0.

- [ ] **Step 4: Force-fire test**

Boot API. Manually inflate a node's support count to push curiosity high, then investigate:
```bash
# After a few real cycles, pick a node:
curl -s http://localhost:8000/api/behavioral-graph | jq '.nodes[0].slug'
# Force investigate:
curl -s -X POST http://localhost:8000/api/curiosity/investigate/<that-slug> | jq .
# Verify a paper page appears:
ls wiki/sources/openalex/ | head
```
Expected (with `OPENALEX_API_KEY` set): at least one new `.md` file under `wiki/sources/openalex/` and the corresponding student's `literature.md` updated.

- [ ] **Step 5: Commit**

```bash
git add intelligence/api/services/kg_agent.py
git commit -m "phase3: wire kg_agent to curiosity gate; write paper pages to wiki/sources/openalex/

Curiosity becomes the third research trigger (OR with thin-patterns and red-severity).
Paper pages written as markdown; student literature.md gets a link.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

**End of Phase 3.** Curiosity score visible in node frontmatter; gate fires research with cooldown; paper pages exist as wiki sources.

---

## Phase 4 — Visualizer rebuild (parallel-developable against Phase 0 stubs)

Goal: implement the three routes (`/`, `/wiki`, `/console`) and the God Mode slide-in panel as specified in `VISION.md`. Reads via the new API endpoints from Phase 0.

> Read `VISION.md` § 5 ("Page-by-page specifications") and § 6 ("Visual language") before writing any frontend code in this phase. Treat that document as the source of truth for layout, interactions, and visual encoding. The component tasks below describe responsibilities, not pixel-perfect specs.

### Task 4.1: Frontend dependencies + API client

**Files:**
- Modify: `backend_visualizer/package.json`
- Modify: `backend_visualizer/app/lib/api.ts` (or create if absent — check first)

- [ ] **Step 1: Add deps**

```bash
cd backend_visualizer
npm install react-force-graph-2d react-markdown remark-gfm remark-wiki-link unified
npm install --save-dev @types/d3
cd ..
```

- [ ] **Step 2: Verify build still works**

```bash
cd backend_visualizer && npm run build
```
Expected: build succeeds (warnings OK, errors not).

- [ ] **Step 3: Find existing API client**

Run: `find backend_visualizer/app -name 'api.ts' -o -name 'api.tsx'`

If one exists, extend it. If not, create `backend_visualizer/app/lib/api.ts`:

```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}
async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}
async function patch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export type BehavioralNode = {
  slug: string; type: string; title: string; summary: string;
  support_count: number; students_count: number; literature_refs: number;
  curiosity_score: number; curiosity_factors: Record<string, number>;
  last_observed_at: string | null; last_research_fetched_at: string | null;
  created_at: string; file_path: string;
};
export type BehavioralEdge = {
  src_slug: string; rel: string; dst_slug: string;
  support_count: number; students_count: number;
  first_observed_at: string; last_observed_at: string;
};
export type StudentIncident = {
  id: number; student_name: string; note_id: number; severity: string;
  ingested_at: string; file_path: string; behavioral_ref_slugs: string[];
};
export type Persona = {
  name: string; age_band: string;
  temperament_axes: Record<string, string>;
  dysfunction_flavor: string; recurring_companions: string[];
  narrative: string; file_path: string;
};
export type CuriosityEvent = {
  id: number; node_slug: string; fired_at: string;
  curiosity_score: number; factors: Record<string, number>;
  triggered_research: boolean; paper_count: number;
};
export type WikiTreeFile = { path: string; mtime: number };
export type WikiPage = { path: string; frontmatter: Record<string, unknown>; body: string; raw: string };

export const api = {
  behavioralGraph: (minSupport = 1) =>
    get<{ nodes: BehavioralNode[]; edges: BehavioralEdge[] }>(`/api/behavioral-graph?min_support=${minSupport}`),
  studentGraph: (name: string) =>
    get<{ student_name: string; incidents: StudentIncident[] }>(`/api/student-graph/${encodeURIComponent(name)}`),
  studentResearch: (name: string) =>
    get<{ student_name: string; papers: any[] }>(`/api/student-graph/${encodeURIComponent(name)}/research`),
  personas: () => get<{ personas: Persona[]; overrides: Record<string, any>; stub?: boolean }>("/api/personas"),
  updatePersona: (name: string, body: { slider?: number; flavor_override?: string; activity_weight?: number }) =>
    patch(`/api/personas/${encodeURIComponent(name)}`, body),
  injectPersona: (name: string, flavor: string) =>
    post(`/api/personas/${encodeURIComponent(name)}/inject`, { flavor }),
  interactPersonas: (a: string, b: string, scene_hint?: string) =>
    post(`/api/personas/interact`, { a, b, scene_hint }),
  curiosityEvents: (limit = 50) =>
    get<{ events: CuriosityEvent[] }>(`/api/curiosity/events?limit=${limit}`),
  curiosityWeights: (weights: Record<string, number>) =>
    patch(`/api/runtime/curiosity-weights`, weights),
  curiosityInvestigate: (slug: string) =>
    post(`/api/curiosity/investigate/${encodeURIComponent(slug)}`),
  wikiTree: () => get<{ root: string; files: WikiTreeFile[] }>("/api/wiki/tree"),
  wikiPage: (path: string) => get<WikiPage>(`/api/wiki/page?path=${encodeURIComponent(path)}`),
  wikiReindex: () => post<{ nodes: number; edges: number; incidents: number; profiles: number }>("/api/wiki/reindex"),
  demoOverview: () => get<any>("/api/demo/overview"),
  demoStart: () => post<any>("/api/demo/start"),
  demoStop: () => post<any>("/api/demo/stop"),
  demoReset: () => post<any>("/api/demo/reset"),
};
```

- [ ] **Step 4: Commit**

```bash
git add backend_visualizer/package.json backend_visualizer/package-lock.json backend_visualizer/app/lib/api.ts
git commit -m "phase4: add react-force-graph-2d/react-markdown deps; extend API client for new endpoints

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.2: Top app bar + route shells

**Files:**
- Create: `backend_visualizer/app/components/TopAppBar.tsx`
- Modify: `backend_visualizer/app/layout.tsx`
- Create: `backend_visualizer/app/wiki/page.tsx`
- Create: `backend_visualizer/app/console/page.tsx`

- [ ] **Step 1: Write `TopAppBar.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/app/lib/api";

export function TopAppBar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<string>("Idle");

  useEffect(() => {
    const tick = async () => {
      try {
        const o = await api.demoOverview();
        const mode = o?.runtime?.mode || "idle";
        setStatus(mode.charAt(0).toUpperCase() + mode.slice(1));
      } catch {
        setStatus("Unreachable");
      }
    };
    tick();
    const i = setInterval(tick, 3000);
    return () => clearInterval(i);
  }, []);

  const link = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`px-3 py-1 rounded ${active ? "bg-white/10 text-white" : "text-white/60 hover:text-white"}`}
      >
        {label}
      </Link>
    );
  };

  const statusColor =
    status === "Running" ? "bg-emerald-500" :
    status === "Idle" ? "bg-zinc-500" :
    status === "Resetting" ? "bg-amber-500" :
    status === "Stopped" ? "bg-rose-500" :
    "bg-zinc-700";

  return (
    <header className="h-12 border-b border-white/10 bg-black flex items-center px-4 gap-4">
      <div className="font-mono font-semibold tracking-wide text-white">monty</div>
      <nav className="flex gap-1">
        {link("/", "Live")}
        {link("/wiki", "Wiki")}
        {link("/console", "Console")}
      </nav>
      <div className="ml-auto flex items-center gap-2 text-xs text-white/80">
        <span className={`w-2 h-2 rounded-full ${statusColor}`} />
        <span>{status}</span>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Update `app/layout.tsx`**

If `layout.tsx` does not already use `TopAppBar`, wrap children in it. Inspect the existing file first; minimum change is to import and render `<TopAppBar />` above `{children}` in the body.

- [ ] **Step 3: Create empty route shells for wiki and console**

`backend_visualizer/app/wiki/page.tsx`:
```tsx
"use client";
export default function WikiPage() {
  return <div className="p-6 text-white/70 font-mono">Wiki Browser — implemented in Tasks 4.10–4.12.</div>;
}
```

`backend_visualizer/app/console/page.tsx`:
```tsx
"use client";
export default function ConsolePage() {
  return <div className="p-6 text-white/70 font-mono">Console — implemented in Task 4.13.</div>;
}
```

- [ ] **Step 4: Build + verify**

```bash
cd backend_visualizer && npm run build
```
Expected: build succeeds; navigation works between `/`, `/wiki`, `/console` in dev mode.

- [ ] **Step 5: Commit**

```bash
git add backend_visualizer/app/
git commit -m "phase4: add TopAppBar with route nav and demo status; stub /wiki and /console routes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.3: `BehavioralKGPanel` — top panel of `/`

**Files:**
- Create: `backend_visualizer/app/components/BehavioralKGPanel.tsx`

- [ ] **Step 1: Write the panel**

```tsx
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { api, type BehavioralNode, type BehavioralEdge } from "@/app/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const TYPE_COLORS: Record<string, string> = {
  setting_event: "#7c3aed",     // violet
  antecedent: "#0ea5e9",         // sky
  behavior: "#f97316",           // orange
  function: "#10b981",           // emerald
  brain_state: "#eab308",        // amber-yellow (NB: distinct from severity yellow via context)
  response: "#ec4899",           // pink
  protective_factor: "#94a3b8",  // muted slate
};

const REL_COLORS: Record<string, string> = {
  triggers: "#0ea5e9",
  serves: "#10b981",
  occurs_in: "#eab308",
  reinforces: "#22c55e",
  extinguishes: "#ef4444",
  "co-regulates": "#a855f7",
  recurs_with: "#f97316",
  predisposes: "#7c3aed",
  amplifies: "#f43f5e",
  gates: "#06b6d4",
  follows: "#94a3b8",
  evidences: "#10b981",
  undermines: "#ef4444",
};

export function BehavioralKGPanel({
  selectedSlug,
  onSelectNode,
}: {
  selectedSlug: string | null;
  onSelectNode: (slug: string | null) => void;
}) {
  const [nodes, setNodes] = useState<BehavioralNode[]>([]);
  const [edges, setEdges] = useState<BehavioralEdge[]>([]);
  const [minSupport, setMinSupport] = useState(2);
  const fgRef = useRef<any>(null);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.behavioralGraph(minSupport);
        if (!stop) { setNodes(r.nodes); setEdges(r.edges); }
      } catch {}
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => { stop = true; clearInterval(i); };
  }, [minSupport]);

  const data = useMemo(() => ({
    nodes: nodes.map(n => ({
      id: n.slug,
      name: n.title || n.slug,
      type: n.type,
      val: Math.max(2, Math.log2(1 + n.support_count) * 4),
      color: TYPE_COLORS[n.type] || "#6b7280",
      curiosity: n.curiosity_score,
    })),
    links: edges.map(e => ({
      source: e.src_slug.split("/").pop()!,
      target: e.dst_slug.split("/").pop()!,
      width: Math.max(0.5, Math.log2(1 + e.support_count)),
      color: REL_COLORS[e.rel] || "#52525b",
      rel: e.rel,
    })),
  }), [nodes, edges]);

  return (
    <div className="relative h-full w-full bg-zinc-950">
      <div className="absolute top-2 left-2 z-10 bg-black/70 rounded p-2 text-xs text-white/80 font-mono">
        <div className="font-semibold mb-1">Behavioral KG (anonymized)</div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
          {Object.entries(TYPE_COLORS).map(([t, c]) => (
            <div key={t} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ background: c }} />
              <span>{t.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute top-2 right-2 z-10 bg-black/70 rounded p-2 text-xs text-white/80 font-mono flex items-center gap-2">
        <label>min support</label>
        <input
          type="number" min={1} value={minSupport}
          onChange={e => setMinSupport(Math.max(1, parseInt(e.target.value || "1")))}
          className="bg-zinc-800 px-2 py-0.5 w-12 rounded"
        />
      </div>
      <ForceGraph2D
        ref={fgRef as any}
        graphData={data}
        nodeRelSize={4}
        linkWidth={(l: any) => l.width}
        linkColor={(l: any) => l.color}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const r = node.val;
          // halo
          if (node.curiosity >= 0.7) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 6, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
            ctx.fill();
          } else if (node.curiosity >= 0.5) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(234, 179, 8, 0.25)";
            ctx.fill();
          }
          // node body
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = node.id === selectedSlug ? "white" : node.color;
          ctx.fill();
          if (globalScale > 1.6) {
            ctx.fillStyle = "white";
            ctx.font = `${10 / globalScale * 4}px sans-serif`;
            ctx.fillText(node.name, node.x + r + 2, node.y + 3);
          }
        }}
        onNodeClick={(node: any) => onSelectNode(node.id === selectedSlug ? null : node.id)}
      />
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd backend_visualizer && npm run build
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add backend_visualizer/app/components/BehavioralKGPanel.tsx
git commit -m "phase4: add BehavioralKGPanel — anonymized force-directed graph with type colors, curiosity halos, edge weight

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.4: `StageRail`, `StudentTimeline`, `IncidentDrawer`

**Files:**
- Create: `backend_visualizer/app/components/StageRail.tsx`
- Create: `backend_visualizer/app/components/StudentTimeline.tsx`
- Create: `backend_visualizer/app/components/IncidentDrawer.tsx`

- [ ] **Step 1: Write `StageRail.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/app/lib/api";

const STAGES = [
  "waiting_for_note", "ingesting_note", "reassessing_student",
  "updating_profile", "enriching_knowledge", "writing_alert", "cycle_complete",
];

export function StageRail() {
  const [stage, setStage] = useState<string>("waiting_for_note");
  useEffect(() => {
    const tick = async () => {
      try {
        const o = await api.demoOverview();
        setStage(o?.runtime?.current_stage || "waiting_for_note");
      } catch {}
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="h-10 flex items-center justify-between px-4 bg-zinc-950 border-y border-white/10 font-mono text-[11px]">
      {STAGES.map((s, idx) => {
        const active = s === stage;
        const passed = STAGES.indexOf(stage) > idx;
        return (
          <div key={s} className={`flex items-center gap-1 ${active ? "text-white" : passed ? "text-white/40" : "text-white/30"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : passed ? "bg-emerald-700" : "bg-zinc-700"}`} />
            <span>{s.replace(/_/g, " ")}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Write `StudentTimeline.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api, type StudentIncident, type Persona } from "@/app/lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  red: "bg-rose-500", yellow: "bg-amber-400", green: "bg-emerald-500", "": "bg-zinc-600",
};

export function StudentTimeline({
  highlightSlug,
  onOpenIncident,
}: {
  highlightSlug: string | null;
  onOpenIncident: (incident: StudentIncident) => void;
}) {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<StudentIncident[]>([]);

  useEffect(() => {
    api.personas().then(r => {
      setPersonas(r.personas);
      if (!active && r.personas.length) setActive(r.personas[0].name);
    });
  }, []);

  useEffect(() => {
    if (!active) return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.studentGraph(active);
        if (!stop) setIncidents(r.incidents);
      } catch {}
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => { stop = true; clearInterval(i); };
  }, [active]);

  return (
    <div className="h-full flex flex-col bg-zinc-950 border-t border-white/10">
      <div className="flex gap-2 p-2 overflow-x-auto">
        {personas.map(p => (
          <button
            key={p.name}
            onClick={() => setActive(p.name)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded font-mono text-xs border ${active === p.name ? "border-white bg-white/5" : "border-white/10 hover:border-white/30"}`}
          >
            <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-white">
              {p.name.charAt(0)}
            </span>
            <span className="text-white">{p.name}</span>
            <span className="text-white/40">·</span>
            <span className="text-white/60">{p.age_band}</span>
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-hidden flex gap-2 p-3">
        {incidents.length === 0 && (
          <div className="text-white/40 text-sm self-center">No observations yet for {active} — try ⚡ God Mode → Inject Note.</div>
        )}
        {[...incidents].reverse().map(inc => {
          const highlighted = highlightSlug && inc.behavioral_ref_slugs.some(s => s.endsWith(highlightSlug));
          const ago = (() => {
            const t = new Date(inc.ingested_at).getTime();
            const s = Math.max(0, (Date.now() - t) / 1000);
            return s < 60 ? `${Math.round(s)}s ago` : s < 3600 ? `${Math.round(s/60)}m ago` : `${Math.round(s/3600)}h ago`;
          })();
          return (
            <button
              key={inc.id}
              onClick={() => onOpenIncident(inc)}
              className={`shrink-0 w-56 text-left p-3 rounded border transition ${highlighted ? "border-white shadow-[0_0_12px_rgba(255,255,255,0.5)]" : "border-white/10 hover:border-white/30"} bg-zinc-900`}
            >
              <div className="flex items-center justify-between font-mono text-[10px] text-white/50">
                <span>{ago}</span>
                <span className={`w-2 h-2 rounded-full ${SEVERITY_COLORS[inc.severity || ""]}`} />
              </div>
              <div className="mt-2 text-xs text-white/80">note #{inc.note_id}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {inc.behavioral_ref_slugs.slice(0, 6).map(s => (
                  <span key={s} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/60">{s.split("/").slice(-2, -1)[0]}</span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write `IncidentDrawer.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type StudentIncident, type WikiPage } from "@/app/lib/api";

export function IncidentDrawer({
  incident, onClose, onSelectBehavioralNode,
}: {
  incident: StudentIncident | null;
  onClose: () => void;
  onSelectBehavioralNode: (slug: string) => void;
}) {
  const [page, setPage] = useState<WikiPage | null>(null);
  useEffect(() => {
    if (!incident) { setPage(null); return; }
    api.wikiPage(incident.file_path).then(setPage).catch(() => {});
  }, [incident?.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!incident) return null;
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute top-0 right-0 h-full w-[720px] max-w-[95vw] bg-zinc-950 border-l border-white/20 overflow-y-auto p-6 text-white/90">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-mono text-sm text-white/60">{incident.file_path}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white">esc</button>
        </div>
        {page ? (
          <>
            <div className="mb-4 text-xs text-white/60 font-mono whitespace-pre">
              {Object.entries(page.frontmatter).map(([k, v]) => (
                <div key={k}>{k}: {Array.isArray(v) ? v.join(", ") : String(v)}</div>
              ))}
            </div>
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{page.body}</ReactMarkdown>
            </div>
            <div className="mt-6">
              <h3 className="font-mono text-xs text-white/60 mb-2">Linked behavioral nodes</h3>
              <div className="flex flex-wrap gap-2">
                {(page.frontmatter.behavioral_refs as string[] | undefined)?.map(ref => {
                  const slug = ref.split("/").slice(-1)[0];
                  return (
                    <button
                      key={ref}
                      onClick={() => { onSelectBehavioralNode(slug); onClose(); }}
                      className="text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10"
                    >
                      {ref}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        ) : <div className="text-white/40">loading…</div>}
      </aside>
    </div>
  );
}
```

- [ ] **Step 4: Build**

```bash
cd backend_visualizer && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add backend_visualizer/app/components/StageRail.tsx backend_visualizer/app/components/StudentTimeline.tsx backend_visualizer/app/components/IncidentDrawer.tsx
git commit -m "phase4: add StageRail, StudentTimeline (with cross-highlight), IncidentDrawer

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.5: God Mode panel components

**Files:**
- Create: `backend_visualizer/app/components/GodModePanel.tsx`
- Create: `backend_visualizer/app/components/PersonaCard.tsx`
- Create: `backend_visualizer/app/components/StoryPresetRow.tsx`
- Create: `backend_visualizer/app/components/CuriosityTuning.tsx`
- Create: `backend_visualizer/app/components/ManualResearchTrigger.tsx`

- [ ] **Step 1: `PersonaCard.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api, type Persona } from "@/app/lib/api";

export function PersonaCard({ persona, override, otherPersonas }: { persona: Persona; override: any; otherPersonas: string[] }) {
  const [slider, setSlider] = useState<number>(override?.slider ?? 0);
  const [flavor, setFlavor] = useState<string>(override?.flavor_override ?? persona.dysfunction_flavor);
  const [activity, setActivity] = useState<number>(override?.activity_weight ?? 1);

  const flavors = ["impulsive", "clingy-then-shutdown", "scattered", "explosive-then-shutdown", "shutdown"];

  const update = async (patch: any) => { await api.updatePersona(persona.name, patch); };

  return (
    <div className="border border-white/10 rounded-lg p-3 bg-zinc-900/80">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="font-semibold text-white">{persona.name}</span>
          <span className="ml-2 text-xs text-white/50">{persona.age_band}</span>
        </div>
        <span className="text-[10px] text-white/40 font-mono">{persona.dysfunction_flavor}</span>
      </div>
      <label className="block text-[10px] text-white/60 mb-1">Functional ↔ Dysfunctional ({slider.toFixed(1)})</label>
      <input
        type="range" min={-1} max={1} step={0.1} value={slider}
        onChange={e => { const v = parseFloat(e.target.value); setSlider(v); update({ slider: v }); }}
        className="w-full accent-rose-400"
        style={{ background: "linear-gradient(to right, #10b981, #eab308, #ef4444)" }}
      />
      <div className="flex gap-2 mt-2">
        <select
          value={flavor}
          onChange={e => { setFlavor(e.target.value); update({ flavor_override: e.target.value }); }}
          className="bg-zinc-800 text-xs px-2 py-1 rounded border border-white/10 flex-1"
        >
          {flavors.map(f => <option key={f}>{f}</option>)}
        </select>
        <input
          type="number" min={0} max={3} step={0.1} value={activity}
          onChange={e => { const v = parseFloat(e.target.value); setActivity(v); update({ activity_weight: v }); }}
          className="bg-zinc-800 text-xs px-2 py-1 rounded border border-white/10 w-16"
          title="activity weight"
        />
      </div>
      <div className="flex gap-1 mt-2">
        {["neutral", "problematic", "emergency", "surprise"].map(f => (
          <button
            key={f}
            onClick={() => api.injectPersona(persona.name, f)}
            className="flex-1 text-[10px] py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 capitalize"
          >
            {f}
          </button>
        ))}
      </div>
      <div className="flex gap-1 mt-2 items-center">
        <span className="text-[10px] text-white/50">interact:</span>
        <select
          onChange={e => api.interactPersonas(persona.name, e.target.value)}
          className="bg-zinc-800 text-[10px] px-2 py-1 rounded border border-white/10 flex-1"
          defaultValue=""
        >
          <option value="">— pick peer —</option>
          {otherPersonas.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: `StoryPresetRow.tsx`**

```tsx
"use client";
import { api } from "@/app/lib/api";

const PRESETS: Record<string, Record<string, { slider: number; activity_weight: number }>> = {
  "Calm Morning": {
    "Arjun Nair": { slider: -0.4, activity_weight: 1 },
    "Diya Malhotra": { slider: -0.5, activity_weight: 1 },
    "Kiaan Gupta": { slider: -0.7, activity_weight: 1 },
    "Mira Shah": { slider: -0.3, activity_weight: 1 },
    "Saanvi Verma": { slider: -0.5, activity_weight: 1 },
  },
  "Escalating Mira": {
    "Arjun Nair": { slider: 0.0, activity_weight: 0.8 },
    "Diya Malhotra": { slider: 0.0, activity_weight: 0.8 },
    "Kiaan Gupta": { slider: -0.3, activity_weight: 0.8 },
    "Mira Shah": { slider: 0.7, activity_weight: 2.0 },
    "Saanvi Verma": { slider: 0.0, activity_weight: 0.8 },
  },
  "Group Conflict": {
    "Arjun Nair": { slider: 0.5, activity_weight: 1.5 },
    "Diya Malhotra": { slider: 0.6, activity_weight: 1.5 },
    "Kiaan Gupta": { slider: 0.3, activity_weight: 1 },
    "Mira Shah": { slider: 0.6, activity_weight: 1.5 },
    "Saanvi Verma": { slider: 0.4, activity_weight: 1 },
  },
  "Emergency Cascade": {
    "Arjun Nair": { slider: 0.8, activity_weight: 1.5 },
    "Diya Malhotra": { slider: 0.8, activity_weight: 1.5 },
    "Kiaan Gupta": { slider: 0.7, activity_weight: 1 },
    "Mira Shah": { slider: 0.95, activity_weight: 2.5 },
    "Saanvi Verma": { slider: 0.7, activity_weight: 1 },
  },
  "Reset to Baseline": {
    "Arjun Nair": { slider: 0, activity_weight: 1 },
    "Diya Malhotra": { slider: 0, activity_weight: 1 },
    "Kiaan Gupta": { slider: 0, activity_weight: 1 },
    "Mira Shah": { slider: 0, activity_weight: 1 },
    "Saanvi Verma": { slider: 0, activity_weight: 1 },
  },
};

export function StoryPresetRow() {
  const apply = async (name: string) => {
    const preset = PRESETS[name];
    await Promise.all(Object.entries(preset).map(([n, v]) => api.updatePersona(n, v)));
  };
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {Object.keys(PRESETS).map(p => (
        <button key={p} onClick={() => apply(p)} className="px-3 py-2 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white">
          {p}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: `CuriosityTuning.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/app/lib/api";

const KEYS = ["novelty", "recurrence_gap", "cross_student", "surprise", "severity_weight", "recency"];
const DEFAULTS = { novelty: 0.20, recurrence_gap: 0.20, cross_student: 0.20, surprise: 0.15, severity_weight: 0.15, recency: 0.10 };

export function CuriosityTuning() {
  const [open, setOpen] = useState(false);
  const [w, setW] = useState<Record<string, number>>({ ...DEFAULTS });
  const update = (k: string, v: number) => {
    const next = { ...w, [k]: v }; setW(next); api.curiosityWeights({ [k]: v });
  };
  return (
    <div className="mt-4 border border-white/10 rounded">
      <button onClick={() => setOpen(o => !o)} className="w-full text-left px-3 py-2 text-xs text-white/70 font-mono">
        {open ? "▼" : "▶"} Curiosity tuning
      </button>
      {open && (
        <div className="p-3 space-y-2">
          {KEYS.map(k => (
            <div key={k}>
              <label className="block text-[10px] text-white/60">{k}: {w[k].toFixed(2)}</label>
              <input
                type="range" min={0} max={0.5} step={0.01} value={w[k]}
                onChange={e => update(k, parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: `ManualResearchTrigger.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/app/lib/api";

export function ManualResearchTrigger() {
  const [slug, setSlug] = useState("");
  const [last, setLast] = useState<any>(null);
  const fire = async () => {
    if (!slug.trim()) return;
    const r = await api.curiosityInvestigate(slug.trim());
    setLast(r);
  };
  return (
    <div className="mt-4 border border-white/10 rounded p-3">
      <div className="text-xs text-white/70 font-mono mb-2">Manual research trigger</div>
      <div className="flex gap-2">
        <input
          value={slug} onChange={e => setSlug(e.target.value)} placeholder="behavioral node slug"
          className="bg-zinc-800 px-2 py-1 rounded text-xs border border-white/10 flex-1 text-white"
        />
        <button onClick={fire} className="px-3 py-1 text-xs rounded bg-rose-600 hover:bg-rose-500 text-white">Investigate</button>
      </div>
      {last && (
        <div className="mt-2 text-[10px] font-mono text-white/60">
          fire={String(last.fire)} score={last.score} reason={last.reason}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: `GodModePanel.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api, type Persona } from "@/app/lib/api";
import { PersonaCard } from "./PersonaCard";
import { StoryPresetRow } from "./StoryPresetRow";
import { CuriosityTuning } from "./CuriosityTuning";
import { ManualResearchTrigger } from "./ManualResearchTrigger";

export function GodModePanel() {
  const [open, setOpen] = useState(false);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [overrides, setOverrides] = useState<Record<string, any>>({});

  useEffect(() => {
    if (!open) return;
    const tick = async () => {
      const r = await api.personas();
      setPersonas(r.personas);
      setOverrides(r.overrides || {});
    };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-30 px-4 py-3 rounded-full bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold shadow-lg"
      >
        ⚡ God Mode
      </button>
      {open && (
        <div className="fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <aside className="absolute top-0 right-0 h-full w-[420px] bg-zinc-950/95 backdrop-blur border-l border-white/20 overflow-y-auto p-4 text-white">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-sm font-mono">⚡ God Mode</h2>
              <button onClick={() => setOpen(false)} className="text-white/50 text-xs">esc</button>
            </div>
            <StoryPresetRow />
            <div className="space-y-3">
              {personas.map(p => (
                <PersonaCard
                  key={p.name}
                  persona={p}
                  override={overrides[p.name] || {}}
                  otherPersonas={personas.filter(x => x.name !== p.name).map(x => x.name)}
                />
              ))}
            </div>
            <CuriosityTuning />
            <ManualResearchTrigger />
            <div className="mt-4 flex gap-2">
              <button onClick={() => api.demoStart()} className="flex-1 px-3 py-2 rounded bg-emerald-600 text-xs">Start</button>
              <button onClick={() => api.demoReset()} className="flex-1 px-3 py-2 rounded bg-amber-600 text-xs">Reset</button>
              <button onClick={() => api.demoStop()} className="flex-1 px-3 py-2 rounded bg-rose-700 text-xs">Stop</button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 6: Build + commit**

```bash
cd backend_visualizer && npm run build
cd ..
git add backend_visualizer/app/components/PersonaCard.tsx backend_visualizer/app/components/StoryPresetRow.tsx backend_visualizer/app/components/CuriosityTuning.tsx backend_visualizer/app/components/ManualResearchTrigger.tsx backend_visualizer/app/components/GodModePanel.tsx
git commit -m "phase4: God Mode slide-in panel with persona cards, presets, curiosity tuning, manual research

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.6: Wire `/` route — compose Live page

**Files:**
- Modify: `backend_visualizer/app/page.tsx`

- [ ] **Step 1: Replace `app/page.tsx` body**

```tsx
"use client";
import { useState } from "react";
import { BehavioralKGPanel } from "./components/BehavioralKGPanel";
import { StageRail } from "./components/StageRail";
import { StudentTimeline } from "./components/StudentTimeline";
import { IncidentDrawer } from "./components/IncidentDrawer";
import { GodModePanel } from "./components/GodModePanel";
import type { StudentIncident } from "./lib/api";

export default function LivePage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [openIncident, setOpenIncident] = useState<StudentIncident | null>(null);

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      <div className="flex-[1.1] min-h-0">
        <BehavioralKGPanel selectedSlug={selectedSlug} onSelectNode={setSelectedSlug} />
      </div>
      <StageRail />
      <div className="flex-1 min-h-0">
        <StudentTimeline highlightSlug={selectedSlug} onOpenIncident={setOpenIncident} />
      </div>
      <IncidentDrawer
        incident={openIncident}
        onClose={() => setOpenIncident(null)}
        onSelectBehavioralNode={setSelectedSlug}
      />
      <GodModePanel />
    </div>
  );
}
```

- [ ] **Step 2: Build + manual demo check**

```bash
cd backend_visualizer && npm run build && npm run dev &
sleep 2
open http://localhost:3200
```
Click into the page. Verify behavioral graph renders (likely empty until streamer is running), persona chips appear, stage rail visible, ⚡ God Mode opens the slide-in.

- [ ] **Step 3: Commit**

```bash
git add backend_visualizer/app/page.tsx
git commit -m "phase4: compose / route — BehavioralKGPanel + StageRail + StudentTimeline + IncidentDrawer + GodModePanel

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.7: Wiki Browser components and `/wiki` route

**Files:**
- Create: `backend_visualizer/app/components/WikiFileTree.tsx`
- Create: `backend_visualizer/app/components/WikiPageRenderer.tsx`
- Create: `backend_visualizer/app/components/WikiBacklinks.tsx`
- Modify: `backend_visualizer/app/wiki/page.tsx`

- [ ] **Step 1: `WikiFileTree.tsx`** — file tree with live-pulse on recent writes

```tsx
"use client";
import { useEffect, useMemo, useState } from "react";
import { api, type WikiTreeFile } from "@/app/lib/api";

type Node = { name: string; path?: string; mtime?: number; children?: Node[] };

function buildTree(files: WikiTreeFile[]): Node {
  const root: Node = { name: "wiki", children: [] };
  for (const f of files) {
    const parts = f.path.split("/");
    let cur = root;
    parts.forEach((part, i) => {
      const isFile = i === parts.length - 1;
      const next = (cur.children = cur.children || []);
      let child = next.find(n => n.name === part);
      if (!child) {
        child = isFile ? { name: part, path: f.path, mtime: f.mtime } : { name: part, children: [] };
        next.push(child);
      }
      cur = child;
    });
  }
  return root;
}

function NodeView({ node, onSelect, selected }: { node: Node; onSelect: (p: string) => void; selected: string | null }) {
  const [open, setOpen] = useState(true);
  if (node.children) {
    return (
      <div>
        <button onClick={() => setOpen(o => !o)} className="text-left text-xs text-white/70 hover:text-white">
          {open ? "▾" : "▸"} {node.name}/
        </button>
        {open && <div className="pl-3">{node.children.map(c => <NodeView key={c.name} node={c} onSelect={onSelect} selected={selected} />)}</div>}
      </div>
    );
  }
  const ago = node.mtime ? (Date.now() / 1000 - node.mtime) : Infinity;
  const cls = ago < 30 ? "bg-emerald-500/20 animate-pulse" : ago < 300 ? "bg-emerald-500/10" : "";
  return (
    <button
      onClick={() => node.path && onSelect(node.path)}
      className={`block w-full text-left text-xs px-1 rounded ${cls} ${selected === node.path ? "text-white bg-white/10" : "text-white/60 hover:text-white"}`}
    >
      {node.name}
    </button>
  );
}

export function WikiFileTree({ selected, onSelect }: { selected: string | null; onSelect: (p: string) => void }) {
  const [files, setFiles] = useState<WikiTreeFile[]>([]);
  const [filter, setFilter] = useState("");
  useEffect(() => {
    const tick = async () => { try { setFiles((await api.wikiTree()).files); } catch {} };
    tick();
    const i = setInterval(tick, 2000);
    return () => clearInterval(i);
  }, []);
  const filtered = useMemo(() => files.filter(f => !filter || f.path.includes(filter)), [files, filter]);
  const tree = useMemo(() => buildTree(filtered), [filtered]);
  return (
    <aside className="w-[280px] border-r border-white/10 bg-zinc-950 overflow-y-auto">
      <input
        value={filter} onChange={e => setFilter(e.target.value)} placeholder="filter…"
        className="w-full bg-zinc-900 px-2 py-1 text-xs border-b border-white/10 text-white"
      />
      <div className="p-2">{tree.children?.map(c => <NodeView key={c.name} node={c} onSelect={onSelect} selected={selected} />)}</div>
    </aside>
  );
}
```

- [ ] **Step 2: `WikiPageRenderer.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type WikiPage } from "@/app/lib/api";

export function WikiPageRenderer({ path, onNavigate }: { path: string | null; onNavigate: (p: string) => void }) {
  const [page, setPage] = useState<WikiPage | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  useEffect(() => {
    if (!path) { setPage(null); return; }
    api.wikiPage(path).then(setPage).catch(() => setPage(null));
  }, [path]);

  if (!path) return <div className="flex-1 p-6 text-white/40">Select a file from the tree.</div>;
  if (!page) return <div className="flex-1 p-6 text-white/40">loading…</div>;

  // Resolve [[wikilinks]] (very small implementation; covers the common case)
  const components = {
    a: (props: any) => {
      const href = props.href || "";
      // For relative .md paths, navigate within wiki view
      if (href.endsWith(".md")) {
        return <a href="#" onClick={e => { e.preventDefault(); onNavigate(href.replace(/^\.\.?\//, "")); }} className="text-sky-400 underline">{props.children}</a>;
      }
      return <a {...props} target="_blank" className="text-sky-400 underline" />;
    },
  };

  return (
    <main className="flex-1 overflow-y-auto p-6 text-white/90">
      <div className="text-xs text-white/50 font-mono mb-1">{page.path}</div>
      <button onClick={() => setShowRaw(r => !r)} className="text-[10px] text-white/40 mb-3 underline">
        {showRaw ? "rendered" : "raw"}
      </button>
      {!showRaw && Object.keys(page.frontmatter).length > 0 && (
        <details open className="mb-4 border border-white/10 rounded p-2 text-xs font-mono">
          <summary className="cursor-pointer text-white/60">frontmatter</summary>
          <pre className="text-white/70">{JSON.stringify(page.frontmatter, null, 2)}</pre>
        </details>
      )}
      {showRaw ? (
        <pre className="text-xs whitespace-pre-wrap text-white/70">{page.raw}</pre>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as any}>{page.body}</ReactMarkdown>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 3: `WikiBacklinks.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api, type WikiTreeFile } from "@/app/lib/api";

export function WikiBacklinks({ path }: { path: string | null }) {
  const [back, setBack] = useState<string[]>([]);
  useEffect(() => {
    if (!path) { setBack([]); return; }
    (async () => {
      const tree = await api.wikiTree();
      const hits: string[] = [];
      for (const f of tree.files) {
        try {
          const page = await api.wikiPage(f.path);
          if (page.body.includes(path) || page.raw.includes(path)) hits.push(f.path);
        } catch {}
      }
      setBack(hits.filter(p => p !== path));
    })();
  }, [path]);
  return (
    <aside className="w-[280px] border-l border-white/10 bg-zinc-950 overflow-y-auto p-3 text-xs text-white/70">
      <div className="font-mono mb-2 text-white/50">Linked from</div>
      {back.length === 0 && <div className="text-white/30">_(none)_</div>}
      {back.map(p => <div key={p} className="py-1">{p}</div>)}
    </aside>
  );
}
```

- [ ] **Step 4: Compose `/wiki` route**

```tsx
"use client";
import { useState } from "react";
import { WikiFileTree } from "../components/WikiFileTree";
import { WikiPageRenderer } from "../components/WikiPageRenderer";
import { WikiBacklinks } from "../components/WikiBacklinks";

export default function WikiPage() {
  const [path, setPath] = useState<string | null>("schema.md");
  return (
    <div className="h-[calc(100vh-3rem)] flex">
      <WikiFileTree selected={path} onSelect={setPath} />
      <WikiPageRenderer path={path} onNavigate={setPath} />
      <WikiBacklinks path={path} />
    </div>
  );
}
```

- [ ] **Step 5: Build + manual check**

```bash
cd backend_visualizer && npm run build && npm run dev &
sleep 2
open http://localhost:3200/wiki
```
Verify file tree renders, clicking files renders content, backlinks pane populates for an incident page.

- [ ] **Step 6: Commit**

```bash
git add backend_visualizer/app/components/WikiFileTree.tsx backend_visualizer/app/components/WikiPageRenderer.tsx backend_visualizer/app/components/WikiBacklinks.tsx backend_visualizer/app/wiki/page.tsx
git commit -m "phase4: Wiki Browser — three-pane Obsidian-style with file tree, renderer, backlinks

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.8: Console route (with curiosity events)

**Files:**
- Create: `backend_visualizer/app/components/CuriosityEventsStream.tsx`
- Modify: `backend_visualizer/app/console/page.tsx`

- [ ] **Step 1: `CuriosityEventsStream.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api, type CuriosityEvent } from "@/app/lib/api";

export function CuriosityEventsStream() {
  const [events, setEvents] = useState<CuriosityEvent[]>([]);
  useEffect(() => {
    const tick = async () => { try { setEvents((await api.curiosityEvents(50)).events); } catch {} };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);
  return (
    <section className="bg-zinc-950 border border-white/10 rounded p-3 font-mono text-xs">
      <div className="text-white/50 mb-2">Curiosity events</div>
      <div className="space-y-1">
        {events.map(ev => (
          <div key={ev.id} className="grid grid-cols-12 gap-2 items-center text-white/80">
            <span className="col-span-2 text-white/40">{new Date(ev.fired_at).toLocaleTimeString()}</span>
            <span className={`col-span-1 ${ev.triggered_research ? "text-emerald-400" : "text-white/30"}`}>{ev.triggered_research ? "fire" : "skip"}</span>
            <span className="col-span-4 truncate">{ev.node_slug}</span>
            <span className="col-span-1 text-right">{ev.curiosity_score.toFixed(2)}</span>
            <span className="col-span-4 text-white/50 truncate">
              {Object.entries(ev.factors).map(([k, v]) => `${k.slice(0,3)}=${(v as number).toFixed(2)}`).join(" ")}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Console page**

```tsx
"use client";
import { useEffect, useState } from "react";
import { CuriosityEventsStream } from "../components/CuriosityEventsStream";
import { api } from "../lib/api";

export default function ConsolePage() {
  const [overview, setOverview] = useState<any>(null);
  useEffect(() => {
    const tick = async () => { try { setOverview(await api.demoOverview()); } catch {} };
    tick();
    const i = setInterval(tick, 1500);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="h-[calc(100vh-3rem)] p-4 space-y-4 overflow-y-auto">
      <section className="bg-zinc-950 border border-white/10 rounded p-3 font-mono text-xs text-white/80">
        <div className="text-white/50 mb-2">Agent status</div>
        <pre className="whitespace-pre-wrap">{JSON.stringify(overview?.runtime, null, 2)}</pre>
      </section>
      <CuriosityEventsStream />
    </div>
  );
}
```

- [ ] **Step 3: Build + commit**

```bash
cd backend_visualizer && npm run build && cd ..
git add backend_visualizer/app/components/CuriosityEventsStream.tsx backend_visualizer/app/console/page.tsx
git commit -m "phase4: Console route with agent status + live curiosity events stream

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

**End of Phase 4.** All three routes live. God Mode operational. Wiki Browser shows files writing in real time.

---

## Phase 5 — Migration & cleanup

Goal: bring legacy DB rows into the wiki, drop deprecated tables, retire the static-corpus generator, and bring the canonical docs (`CLAUDE.md`, `README.md`) in line with the new architecture.

### Task 5.1: One-shot migration script

**Files:**
- Create: `scripts/migrate_to_wiki.py`

- [ ] **Step 1: Write the script**

```python
"""One-shot migration: legacy DB rows -> wiki/ markdown.

Run with --dry-run first to see counts. Then run without --dry-run to
actually write. Idempotent: re-running skips files already present.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import frontmatter

from intelligence.api.services.ghost_client import (
    _connect_agent_db,
    get_all_profiles,
    get_student_snapshots,
    get_student_literature,
)
from intelligence.api.services import wiki_writer, wiki_indexer
from intelligence.api.services.wiki_paths import (
    WIKI_ROOT, source_paper_path, slugify,
)


def migrate_profiles(dry_run: bool) -> int:
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        if not name:
            continue
        if dry_run:
            n += 1; continue
        wiki_writer.update_student_rollups(name)
        n += 1
    return n


def migrate_snapshots(dry_run: bool) -> int:
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        snaps = get_student_snapshots(name) if name else []
        for s in snaps or []:
            if dry_run:
                n += 1; continue
            ts = s.get("snapshot_at") or datetime.now(timezone.utc).isoformat()
            ts = ts if isinstance(ts, str) else ts.isoformat()
            try:
                wiki_writer.write_incident(
                    student_name=name,
                    note_id=s.get("note_id") or 0,
                    severity=s.get("severity") or "yellow",
                    note_body=s.get("profile_summary") or "",
                    interpretation=s.get("behavioral_patterns") or "",
                    behavioral_refs=[],
                    peers_present=[],
                    educator="",
                    ingested_at_iso=ts,
                    slug_hint=slugify(s.get("profile_summary", "")[:60] or f"snap-{s.get('note_id')}"),
                )
                n += 1
            except Exception as e:
                print(f"[snap {name} #{s.get('note_id')}] {e}", file=sys.stderr)
    return n


def migrate_literature(dry_run: bool) -> int:
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        papers = get_student_literature(name) if name else []
        for paper in papers or []:
            if dry_run:
                n += 1; continue
            oid = paper.get("openalex_id", "").split("/")[-1] or f"unknown-{n}"
            path = source_paper_path(oid)
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            meta = {
                "openalex_id": paper.get("openalex_id"),
                "title": paper.get("title"),
                "authors": paper.get("authors", "").split(", ") if paper.get("authors") else [],
                "publication_year": paper.get("publication_year"),
                "cited_by_count": paper.get("cited_by_count", 0),
                "landing_page_url": paper.get("landing_page_url"),
                "fetched_for_query": paper.get("search_query"),
                "fetched_for_student": name,
            }
            body = (
                f"# {paper.get('title')}\n\n"
                f"## Relevance\n\n{paper.get('relevance_summary', '')}\n\n"
                f"## Abstract\n\n{(paper.get('abstract') or '')[:2000]}\n"
            )
            post = frontmatter.Post(content=body, **meta)
            path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print("=== migration ===", "(dry run)" if args.dry_run else "(WRITING)")
    snaps = migrate_snapshots(args.dry_run)
    profs = migrate_profiles(args.dry_run)
    lit = migrate_literature(args.dry_run)
    print(f"snapshots={snaps} profiles={profs} literature={lit}")

    if not args.dry_run:
        print("regenerating indexes…")
        wiki_writer.update_indexes()
        print("rebuilding Postgres index from wiki/…")
        counts = wiki_indexer.full_rebuild()
        print(f"indexed: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry-run**

```bash
python3 -m scripts.migrate_to_wiki --dry-run
```
Expected: prints counts. No files written.

- [ ] **Step 3: Real run**

```bash
python3 -m scripts.migrate_to_wiki
```
Expected: incidents under `wiki/students/<Name>/incidents/`, papers under `wiki/sources/openalex/`, profile rollups exist, Postgres index rebuilt.

- [ ] **Step 4: Lint pass**

```bash
python3 -m scripts.lint_anonymization
```
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_to_wiki.py
git add wiki/
git commit -m "phase5: migrate legacy snapshots, profiles, literature into wiki/

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5.2: Drop legacy tables

**Files:**
- Modify: `intelligence/api/services/ghost_client.py`

- [ ] **Step 1: Add a one-shot script-call to drop legacy tables**

Append to `scripts/migrate_to_wiki.py` an explicit `--drop-legacy` flag that runs:
```python
def drop_legacy() -> None:
    with _connect_agent_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS knowledge_graph CASCADE")
            cur.execute("DROP TABLE IF EXISTS student_personality_graph CASCADE")
            conn.commit()
    print("dropped: knowledge_graph, student_personality_graph")
```

Wire the flag in `main()`:
```python
parser.add_argument("--drop-legacy", action="store_true")
# ...
if args.drop_legacy:
    drop_legacy()
```

- [ ] **Step 2: Run after verifying migration**

```bash
python3 -m scripts.migrate_to_wiki --drop-legacy
```

- [ ] **Step 3: Remove `CREATE TABLE` for legacy tables from `ensure_agent_tables`**

In `intelligence/api/services/ghost_client.py`, locate the `CREATE TABLE` blocks for `knowledge_graph` and `student_personality_graph` and delete them. Also delete any helper functions in this file that only operated on those tables (e.g., `upsert_knowledge_graph_entry`, `get_knowledge_graph_entries`, `upsert_personality_graph_entry`, `get_personality_graph`).

If `kg_agent.py` still imports `upsert_knowledge_graph_entry` or `get_knowledge_graph_entries`, replace those import lines with no-ops or move the calls to the new wiki-writer paper-page logic from Phase 3.

- [ ] **Step 4: Verify boot still works**

```bash
uvicorn intelligence.api.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/health | jq .
kill %1
```
Expected: API boots; no errors about missing imports.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_to_wiki.py intelligence/api/services/ghost_client.py intelligence/api/services/kg_agent.py
git commit -m "phase5: drop legacy knowledge_graph and student_personality_graph tables and helpers

Migration step --drop-legacy run; ensure_agent_tables no longer creates them.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5.3: Remove static corpus generator + unused notes

**Files:**
- Delete: `scripts/generate_notes_corpus.py`

- [ ] **Step 1: Delete**

```bash
git rm scripts/generate_notes_corpus.py
```

- [ ] **Step 2: Optionally remove now-unused `notes_streamer/notes/*.txt`**

These are still on disk but no longer read by the streamer. Decide whether to keep for archival or delete. If deleting:
```bash
git rm -r notes_streamer/notes/
```

(Recommendation: keep them for one demo cycle in case you need to fall back; delete after the demo.)

- [ ] **Step 3: Commit**

```bash
git commit -m "phase5: remove static corpus generator (replaced by persona engine)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5.4: Update `CLAUDE.md` and `README.md`

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Sections to revise:
- "Architecture (Big Picture)" — add `wiki/` as the markdown source-of-truth layer.
- "Databases" — replace mentions of `knowledge_graph` and `student_personality_graph` with `behavioral_nodes`, `behavioral_edges`, `student_incidents`, `student_profiles_index`, `curiosity_events`.
- "Key Conventions (non-obvious)" — add: "wiki/ is the source of truth; Postgres is a derived index synced by wiki_writer", "behavioral pages are anonymized; lint enforced by anonymization_lint.py", "persona engine generates notes live via OpenAI".
- "Common Commands" — add `python3 -m scripts.lint_anonymization`, `python3 -m scripts.migrate_to_wiki`, `python3 -m scripts.verify_persona_engine`. Remove `python3 -m intelligence.api.seed` and the static-corpus mention.
- "Known Caveats" — note that demo cadence depends on live LLM uptime; God Mode `Inject` is the recovery path.

- [ ] **Step 2: Update `README.md`**

Sections to revise:
- "Current State" — strike "legacy seeded flows" wording; the seed scripts are gone.
- "Architecture" — replace ASCII diagram with one that shows persona engine, wiki_writer, behavioral KG, student wikis, curiosity gate.
- "Main Components" — add `intelligence/api/services/wiki_writer.py`, `wiki_indexer.py`, `curiosity.py`, `notes_streamer/persona_engine.py`. Remove `seed.py`/`seed_literature.py` references.
- "APIs" — extend the endpoint list with the new `/api/behavioral-graph`, `/api/student-graph/{name}`, `/api/personas*`, `/api/persona/next-note`, `/api/curiosity/*`, `/api/wiki/*`, `/api/runtime/curiosity-weights`.
- "How to Run" — remove "Optional: run legacy seed flows" subsection.
- "Recommended Demo Flow" — add the God Mode story preset workflow.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "phase5: update CLAUDE.md and README.md to reflect markdown-first wiki + persona engine + curiosity

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5.5: Verify success criteria

Run each of the 7 success criteria from the spec § "Success criteria" and confirm.

- [ ] **Step 1: Cold start with empty wiki body**

```bash
rm -rf wiki/behavioral/setting_events/*.md wiki/behavioral/antecedents/*.md \
  wiki/behavioral/behaviors/*.md wiki/behavioral/functions/*.md \
  wiki/behavioral/brain_states/*.md wiki/behavioral/responses/*.md \
  wiki/behavioral/_edges/*.md wiki/sources/openalex/*.md
rm -rf wiki/students/*/incidents/*.md
curl -s -X POST http://localhost:8000/api/wiki/reindex | jq .
```

- [ ] **Step 2: Boot + run demo for 5 minutes**

Boot all four processes (API, KG agent, streamer, visualizer). Open `/`. Click `Start Live Demo`. Run for 5 minutes.

- [ ] **Step 3: Verify each criterion**

```bash
# 1: Self-extending wiki
ls wiki/behavioral/antecedents/ wiki/students/*/incidents/ | head

# 2: Anonymization clean
python3 -m scripts.lint_anonymization

# 3: Cross-student reinforcement
python3 -c "
import psycopg2.extras
from intelligence.api.services.ghost_client import _connect_agent_db
with _connect_agent_db() as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute('SELECT slug, support_count, students_count FROM behavioral_nodes WHERE students_count >= 3 AND support_count >= 5')
        rows = cur.fetchall()
        print(rows)
"

# 4: Curiosity-driven research
ls wiki/sources/openalex/

# 5: Inject Emergency works (manual click in God Mode)
# 6: Wiki browser pulses (manual visual check)
# 7: VISION.md sufficient (qualitative check — paste into a UI LLM)
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "phase5: success criteria validated; wiki populates, anonymization clean, curiosity fires" \
  --allow-empty
```

---

**End of Phase 5.** Implementation complete.

---

## Self-review

Per the writing-plans skill, this section is filled in by the plan author after writing the full plan. Last cross-check on `2026-04-16`:

**Spec coverage:**
- [x] § "Vision document" — handled by `VISION.md` (committed `7037acc`); plan does not duplicate.
- [x] § "Architecture overview" — Phases 0-3 implement all listed substrates; Phase 0 task 0.4 creates the index tables.
- [x] § "Behavioral KG node schema" — 6 node types + edges enforced via `wiki_paths.BEHAVIORAL_TYPES`; LLM prompt in Task 2.7 references the same vocabulary.
- [x] § "Wiki layout" — Task 0.2 creates the exact directory layout from the spec.
- [x] § "Anonymization wall" — Tasks 0.5 (lint) + 2.2 (writer integration) + 2.8 (CLI lint) + 5.5 step 3 (final check).
- [x] § "Frontmatter contracts" — schemas embedded in Task 2.2, 2.3, 2.4 code.
- [x] § "Live runtime: persona engine + agent loop" — Tasks 1.1-1.3.
- [x] § "Curiosity gate" — Tasks 3.1-3.3.
- [x] § "Visualizer" — Tasks 4.1-4.8 cover Live, Wiki Browser, God Mode, Console.
- [x] § "Postgres index tables" — Task 0.4 creates; Task 5.2 drops legacy.
- [x] § "API surface" — Task 0.6 adds new + replaced endpoints.
- [x] § "Service layout" — file paths match the spec exactly.
- [x] § "Implementation phasing" — six phases preserved 1:1.
- [x] § "Risks & mitigations" — anonymization lint, locks, fallback persona template, cooldown, graceful degradation are all in plan code.
- [x] § "Out of scope" — plan does not introduce auth, markdown editing, vector search, slide-deck export.
- [x] § "Success criteria" — Task 5.5 validates all 7.

**Placeholder scan:** No "TBD"/"TODO"/"implement later" text in any task body. Stub modules in Task 0.5 explicitly `raise NotImplementedError("...— implement in Phase N")` so any caller that hits them before the right phase fails loudly with a pointer to the concrete task.

**Type consistency:** Method names verified: `upsert_behavioral_node`, `upsert_behavioral_edge`, `write_incident`, `update_student_rollups`, `append_log`, `update_indexes`, `compute_factors`, `evaluate_gate`, `generate_next_note`, `list_personas` are spelled identically in stub (Task 0.5), implementation (Tasks 1.x, 2.x, 3.x), and consumer call sites (Tasks 1.3, 2.6, 4.x). API client method names in Task 4.1 match the FastAPI endpoint paths from Task 0.6.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-16-decoupled-kgs-and-llm-wiki.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Phases 1, 2, and 4 can run in parallel after Phase 0; Phase 3 depends on Phase 2; Phase 5 depends on all.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**

