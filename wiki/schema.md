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
