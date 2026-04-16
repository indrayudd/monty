"""Markdown writer for the wiki/ directory.

Single source of truth for any write under wiki/. Enforces anonymization
on writes to wiki/behavioral/. Synchronously calls wiki_indexer after
each write so Postgres index stays in sync.

Full implementation in Phase 2.
"""
from __future__ import annotations

import hashlib
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import frontmatter

from intelligence.api.services.anonymization_lint import assert_clean
from intelligence.api.services.wiki_paths import (
    BEHAVIORAL_TYPES,
    WIKI_ROOT,
    behavioral_edge_path,
    behavioral_node_path,
    incident_path,
    slugify,
    student_dir,
)

_WRITE_LOCK = Lock()


# ---------------------------------------------------------------------------
# Task 2.1 — append_log and update_indexes
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Task 2.2 — upsert_behavioral_node with anonymization lint and SHA256 hashes
# ---------------------------------------------------------------------------


def upsert_behavioral_node(
    node_type: str,
    slug: str,
    title: str,
    summary: str,
    new_evidence: str,
    new_student_name: str | None = None,
) -> dict[str, Any]:
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
                "title": title,
                "support_count": 0,
                "students_count": 0,
                "_student_hashes": [],
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

        # Lint body only — frontmatter contains hashes that don't reveal names.
        assert_clean(body, file_path=path)

        path.write_text(full_text + ("\n" if not full_text.endswith("\n") else ""), encoding="utf-8")

        result = {
            "path": str(path.relative_to(WIKI_ROOT)),
            "support_count": meta["support_count"],
            "students_count": meta["students_count"],
            "created": not path.exists(),
        }

        _index_after_write(path, "behavioral_node")
        return result


# ---------------------------------------------------------------------------
# Task 2.3 — upsert_behavioral_edge
# ---------------------------------------------------------------------------


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

        result = {
            "path": str(path.relative_to(WIKI_ROOT)),
            "support_count": meta["support_count"],
            "students_count": meta["students_count"],
        }

        _index_after_write(path, "behavioral_edge")
        return result


# ---------------------------------------------------------------------------
# Task 2.4 — write_incident and update_student_rollups
# ---------------------------------------------------------------------------


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

        rel_path = str(path.relative_to(WIKI_ROOT))
        _index_after_write(path, "incident")
        return rel_path


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
            # ref is already like "behavioral/antecedents/peer-takes-material"
            # from students/<Name>/, the correct relative path is ../../behavioral/<type>/<slug>.md
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

        profile_path = sdir / "profile.md"
        _index_after_write(profile_path, "profile")


# ---------------------------------------------------------------------------
# Task 2.5 — _index_after_write helper (wires writer to indexer)
# ---------------------------------------------------------------------------


def _index_after_write(path: Path, kind: str) -> None:
    """Sync the just-written file into Postgres. Errors are non-fatal."""
    try:
        from intelligence.api.services import wiki_indexer
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
        print(f"[wiki_writer] index sync failed for {path}: {e}", file=sys.stderr, flush=True)
