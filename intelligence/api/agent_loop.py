from __future__ import annotations

import argparse
import time

from intelligence.api.services.ghost_client import ensure_agent_tables
from intelligence.api.services.self_improve import run_agent_cycle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Monty backend agentic loop.")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--single-shot", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--force-full", action="store_true", help="Ignore runtime checkpoint and reprocess all notes.")
    parser.add_argument("--verbose", action="store_true", help="Print per-student agent actions.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(
        f"[agent-loop] starting with interval={max(args.interval_seconds, 0.0):.1f}s",
        flush=True,
    )
    ensure_agent_tables()

    first_pass = True
    while True:
        summary = run_agent_cycle(force_full=args.force_full and first_pass, verbose=args.verbose)
        print(
            "[agent-loop] "
            f"notes={summary['new_notes']} "
            f"students={summary['students_processed']} "
            f"knowledge+={summary['new_knowledge_nodes']} "
            f"open_alerts={summary['alerts_open']}"
        )
        first_pass = False

        if args.single_shot:
            break

        time.sleep(max(args.interval_seconds, 0.0))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
