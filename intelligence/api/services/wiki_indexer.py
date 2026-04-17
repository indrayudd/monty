"""Sync wiki/ markdown -> SQLite index tables.

Called synchronously by wiki_writer on every write. Also exposes a full
rebuild used by the migration script and POST /api/wiki/reindex.

Full implementation in Phase 2.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from intelligence.api.services.ghost_client import _conn
from intelligence.api.services.wiki_paths import WIKI_ROOT


def _file_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def index_behavioral_node(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    summary = ""
    if "## Summary" in post.content:
        summary = post.content.split("## Summary", 1)[1].split("##", 1)[0].strip()

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO behavioral_nodes (
                slug, type, title, summary,
                support_count, students_count, literature_refs,
                curiosity_score, curiosity_factors,
                last_observed_at, last_research_fetched_at, created_at,
                file_path, file_mtime
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                json.dumps(meta.get("last_curiosity_factors", {})),
                meta.get("last_observed_at"),
                meta.get("last_research_fetched_at"),
                meta.get("created_at"),
                str(file_path.relative_to(WIKI_ROOT)),
                _file_mtime(file_path).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def index_behavioral_edge(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    src_full = meta.get("src_slug", "")
    dst_full = meta.get("dst_slug", "")
    source = meta.get("source", "observation")

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO behavioral_edges (
                src_slug, rel, dst_slug,
                support_count, students_count,
                first_observed_at, last_observed_at,
                file_path, source
            )
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT (src_slug, rel, dst_slug) DO UPDATE SET
                support_count = EXCLUDED.support_count,
                students_count = EXCLUDED.students_count,
                last_observed_at = EXCLUDED.last_observed_at,
                file_path = EXCLUDED.file_path,
                source = EXCLUDED.source
            """,
            (
                src_full, meta.get("rel"), dst_full,
                int(meta.get("support_count", 0)),
                int(meta.get("students_count", 0)),
                meta.get("first_observed_at"),
                meta.get("last_observed_at"),
                str(file_path.relative_to(WIKI_ROOT)),
                source,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def index_student_incident(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    refs = list(meta.get("behavioral_refs", []) or [])

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_incidents (
                student_name, note_id, severity, ingested_at,
                file_path, file_mtime, behavioral_ref_slugs
            )
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                meta.get("student"),
                meta.get("note_id"),
                meta.get("severity"),
                meta.get("ingested_at"),
                str(file_path.relative_to(WIKI_ROOT)),
                _file_mtime(file_path).isoformat(),
                json.dumps(refs),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def index_student_profile(file_path: Path) -> None:
    post = frontmatter.load(file_path)
    meta = post.metadata
    student = meta.get("student")
    if not student:
        return

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_profiles_index (
                student_name, current_severity, trend,
                incident_count, patterns_summary, file_path, file_mtime
            )
            VALUES (?,?,?,?,?,?,?)
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
                _file_mtime(file_path).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def full_rebuild() -> dict[str, int]:
    """Walk wiki/, drop and replay all index tables. Returns counts."""
    counts = {"nodes": 0, "edges": 0, "incidents": 0, "profiles": 0}
    conn = _conn()
    try:
        cur = conn.cursor()
        for table in ["behavioral_nodes", "behavioral_edges", "student_incidents", "student_profiles_index"]:
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()

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
