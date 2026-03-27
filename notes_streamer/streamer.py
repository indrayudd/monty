from __future__ import annotations

from pathlib import Path
import argparse
import random
import sys
import time

from .ghost_build import GhostBuildDatabase, GhostBuildError
from .note_parser import NoteParseError, parse_note_file


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_GHOST_STATE_PATH = PACKAGE_ROOT / ".ghost-build.json"
DEFAULT_NOTES_DIR = PACKAGE_ROOT / "notes"
DEFAULT_GHOST_DATABASE_NAME = "test-db"


def collect_note_paths(notes_dir: Path) -> list[Path]:
    if not notes_dir.exists():
        raise FileNotFoundError(f"Notes directory not found: {notes_dir}")
    return sorted(path for path in notes_dir.glob("*.txt") if path.is_file())


def stream_once(notes_dir: Path, ghost_db: GhostBuildDatabase, rng: random.Random) -> Path:
    note_paths = collect_note_paths(notes_dir)
    if not note_paths:
        raise FileNotFoundError(f"No note files found in {notes_dir}")

    source_path = rng.choice(note_paths)
    parsed = parse_note_file(source_path)
    inserted = ghost_db.insert_note(parsed)
    status = "inserted" if inserted else "skipped"
    print(f"[{status}] {parsed.name}", flush=True)
    return source_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream random Montessori notes into Ghost Build.")
    parser.add_argument("--notes-dir", type=Path, default=DEFAULT_NOTES_DIR)
    parser.add_argument("--ghost-state-path", type=Path, default=DEFAULT_GHOST_STATE_PATH)
    parser.add_argument("--ghost-database-name", default=DEFAULT_GHOST_DATABASE_NAME)
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=0, help="Number of notes to stream; 0 means run forever.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--single-shot", action="store_true", help="Stream exactly one note and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    ghost_db = GhostBuildDatabase(args.ghost_database_name, args.ghost_state_path)

    limit = 1 if args.single_shot else args.limit
    streamed = 0

    try:
        ghost_db.initialize()
        while True:
            stream_once(args.notes_dir, ghost_db, rng)
            streamed += 1
            if limit and streamed >= limit:
                break
            if not args.single_shot:
                time.sleep(max(args.interval_seconds, 0.0))
    except (KeyboardInterrupt, BrokenPipeError):
        return 130
    except (FileNotFoundError, NoteParseError, GhostBuildError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
