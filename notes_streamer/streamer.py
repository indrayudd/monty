from __future__ import annotations

from pathlib import Path
import argparse
import random
import sys
import time

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from notes_streamer.ghost_build import GhostBuildDatabase, GhostBuildError
    from notes_streamer.note_parser import NoteParseError, parse_note_file
else:
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
    parser.add_argument(
        "--ghost-database-id",
        "--table-id",
        dest="ghost_database_id",
        default=None,
        help="Ghost Build database id to reuse if it exists; creates a new database if it does not.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Fixed interval between streamed notes. Defaults to 1 second for demo responsiveness.",
    )
    parser.add_argument("--interval-min-seconds", type=float, default=1.0)
    parser.add_argument("--interval-max-seconds", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0, help="Number of notes to stream; 0 means run forever.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--single-shot", action="store_true", help="Stream exactly one note and exit.")
    return parser


def _next_sleep_seconds(args: argparse.Namespace, rng: random.Random) -> float:
    if args.interval_seconds is not None:
        return max(args.interval_seconds, 0.0)

    low = max(args.interval_min_seconds, 0.0)
    high = max(args.interval_max_seconds, 0.0)
    if high < low:
        raise ValueError("--interval-max-seconds must be >= --interval-min-seconds")
    return rng.uniform(low, high)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    ghost_db = GhostBuildDatabase(args.ghost_database_name, args.ghost_state_path, args.ghost_database_id)

    limit = 1 if args.single_shot else args.limit
    streamed = 0
    note_queue: list[Path] = []

    try:
        print(
            f"[streamer] starting notes stream from {args.notes_dir} "
            f"with interval={_next_sleep_seconds(args, rng):.1f}s",
            flush=True,
        )
        ghost_db.initialize()
        while True:
            if not note_queue:
                note_queue = collect_note_paths(args.notes_dir)
                if not note_queue:
                    raise FileNotFoundError(f"No note files found in {args.notes_dir}")
                rng.shuffle(note_queue)

            source_path = note_queue.pop()
            parsed = parse_note_file(source_path)
            inserted = ghost_db.insert_note(parsed)
            status = "inserted" if inserted else "skipped"
            print(f"[{status}] {parsed.name}", flush=True)
            streamed += 1
            if limit and streamed >= limit:
                break
            if not args.single_shot:
                time.sleep(_next_sleep_seconds(args, rng))
    except (KeyboardInterrupt, BrokenPipeError):
        return 130
    except (FileNotFoundError, NoteParseError, GhostBuildError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
