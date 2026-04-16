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
