"""One-shot migration: legacy DB rows -> wiki/ markdown.

Run with --dry-run first to see counts. Then run without --dry-run to
actually write. Idempotent: re-running skips files already present.

Usage:
    python3 -m scripts.migrate_to_wiki --dry-run
    python3 -m scripts.migrate_to_wiki

    # After migration completes, drop legacy tables (requires explicit confirmation):
    python3 -m scripts.migrate_to_wiki --drop-legacy
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import frontmatter

from intelligence.api.services.ghost_client import (
    _agent_db_url,
    get_all_profiles,
    get_student_snapshots,
    get_student_literature,
)
from intelligence.api.services import wiki_writer, wiki_indexer
from intelligence.api.services.wiki_paths import (
    incident_path,
    source_paper_path,
    slugify,
)


def migrate_profiles(dry_run: bool) -> int:
    """Trigger wiki rollup for each student profile. Idempotent."""
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        if not name:
            continue
        if dry_run:
            n += 1
            continue
        try:
            wiki_writer.update_student_rollups(name)
            n += 1
        except Exception as e:
            print(f"[profile {name}] {e}", file=sys.stderr)
    return n


def migrate_snapshots(dry_run: bool) -> int:
    """Write one incident page per profile_snapshot row. Skips existing files."""
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        if not name:
            continue
        snaps = get_student_snapshots(name) or []
        for s in snaps:
            if dry_run:
                n += 1
                continue
            ts = s.get("snapshot_at") or datetime.now(timezone.utc).isoformat()
            ts = ts if isinstance(ts, str) else ts.isoformat()
            summary = s.get("profile_summary") or ""
            slug_hint = slugify(summary[:60]) or f"snap-{s.get('note_id', n)}"
            expected_path = incident_path(name, ts, slug_hint)
            if expected_path.exists():
                continue  # already migrated
            try:
                wiki_writer.write_incident(
                    student_name=name,
                    note_id=int(s.get("note_id") or 0),
                    severity=s.get("severity") or "yellow",
                    note_body=summary,
                    interpretation=s.get("behavioral_patterns") or "",
                    behavioral_refs=[],
                    peers_present=[],
                    educator="",
                    ingested_at_iso=ts,
                    slug_hint=slug_hint,
                )
                n += 1
            except Exception as e:
                print(f"[snap {name} #{s.get('note_id')}] {e}", file=sys.stderr)
    return n


def migrate_literature(dry_run: bool) -> int:
    """Write one openalex markdown page per student_literature row. Skips existing."""
    profiles = get_all_profiles()
    n = 0
    for p in profiles:
        name = p.get("student_name")
        if not name:
            continue
        papers = get_student_literature(name) or []
        for paper in papers:
            if dry_run:
                n += 1
                continue
            raw_id = paper.get("openalex_id") or ""
            oid = raw_id.split("/")[-1] or f"unknown-{n}"
            path = source_paper_path(oid)
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            authors_raw = paper.get("authors") or ""
            authors_list = [a.strip() for a in authors_raw.split(",")] if authors_raw else []
            meta = {
                "openalex_id": paper.get("openalex_id"),
                "title": paper.get("title"),
                "authors": authors_list,
                "publication_year": paper.get("publication_year"),
                "cited_by_count": int(paper.get("cited_by_count") or 0),
                "landing_page_url": paper.get("landing_page_url"),
                "fetched_for_query": paper.get("search_query"),
                "fetched_for_student": name,
            }
            body = (
                f"# {paper.get('title') or 'Untitled'}\n\n"
                f"## Relevance\n\n{paper.get('relevance_summary') or ''}\n\n"
                f"## Abstract\n\n{(paper.get('abstract') or '')[:2000]}\n"
            )
            post = frontmatter.Post(content=body, **meta)
            try:
                path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
                n += 1
            except Exception as e:
                print(f"[literature {name} {oid}] {e}", file=sys.stderr)
    return n


def drop_legacy() -> int:
    """Drop legacy knowledge_graph and student_personality_graph tables.

    Requires the user to type DROP at the confirmation prompt. Returns 0 on
    success, 1 on cancellation or error.
    """
    print("WARNING: This will DROP knowledge_graph CASCADE and student_personality_graph CASCADE.")
    print("This is irreversible. Only proceed after migrate_to_wiki has populated wiki/ from these tables.")
    try:
        confirm = input("Type DROP to confirm: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.", file=sys.stderr)
        return 1
    if confirm != "DROP":
        print("Confirmation did not match. Aborting.", file=sys.stderr)
        return 1

    import psycopg2
    from psycopg2.extras import RealDictCursor
    url = _agent_db_url()
    try:
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=5)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS knowledge_graph CASCADE")
            cur.execute("DROP TABLE IF EXISTS student_personality_graph CASCADE")
        conn.close()
        print("dropped: knowledge_graph, student_personality_graph")
        return 0
    except Exception as exc:
        print(f"Drop failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate legacy DB rows to wiki/ markdown (one-shot, idempotent)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only, do not write any files.",
    )
    parser.add_argument(
        "--drop-legacy",
        action="store_true",
        help="(NOT YET IMPLEMENTED) Drop legacy DB tables after migration.",
    )
    args = parser.parse_args()

    if args.drop_legacy:
        return drop_legacy()

    mode = "(dry run)" if args.dry_run else "(WRITING)"
    print(f"=== migrate_to_wiki {mode} ===")

    snaps = migrate_snapshots(args.dry_run)
    profs = migrate_profiles(args.dry_run)
    lit = migrate_literature(args.dry_run)

    print(f"snapshots={snaps}  profiles={profs}  literature={lit}")

    if not args.dry_run:
        print("regenerating wiki indexes…")
        wiki_writer.update_indexes()
        print("rebuilding Postgres index from wiki/…")
        counts = wiki_indexer.full_rebuild()
        print(f"indexed: {counts}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
