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
