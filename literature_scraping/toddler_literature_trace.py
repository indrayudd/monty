from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from notes_streamer.ghost_build import GhostBuildDatabase, GhostBuildError, StoredObservation
    from notes_streamer.note_parser import parse_note_file
    from literature_scraping.api_usage_example import (
        OpenAlexClient,
        extract_abstract_text,
    )
else:
    from ..ghost_build import GhostBuildDatabase, GhostBuildError, StoredObservation
    from ..note_parser import parse_note_file
    from .api_usage_example import (
        OpenAlexClient,
        extract_abstract_text,
    )


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_GHOST_STATE_PATH = PROJECT_ROOT / "notes_streamer" / ".ghost-build.json"
DEFAULT_GHOST_DATABASE_NAME = "test-db"
DEFAULT_TRACE_PATH = PROJECT_ROOT / "trace.txt"
DEFAULT_INTERVAL_SECONDS = 5.0
SMOKE_TEST_LIMIT = 3


def load_dotenv_if_present(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _one_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip()
    if sentence and sentence[-1] not in ".!?":
        sentence += "."
    return sentence


@dataclass(frozen=True)
class AnalysisResult:
    query: str
    rationale: str


class ToddlerBehaviorLLMWrapper:
    QUERY_PATTERNS: tuple[tuple[str, str], ...] = (
        ("peer boundary concern", "toddler peer boundaries turn taking"),
        ("voice level reminder", "toddler classroom voice level regulation"),
        ("circle time disruption", "toddler circle time disruption self regulation"),
        ("frustration at the shelf", "toddler frustration self regulation"),
        ("transition difficulty", "toddler transition support early childhood"),
        ("personal space", "toddler personal space peer boundaries"),
        ("turn-taking", "toddler turn taking peer interaction"),
        ("redirected", "toddler redirection classroom behavior"),
        ("escalated", "toddler escalation de-escalation"),
        ("bothered", "toddler frustration regulation"),
        ("unsafe", "toddler classroom behavior boundaries"),
        ("not waiting", "toddler waiting turn-taking behavior"),
    )

    def deduce_query(self, note: StoredObservation) -> AnalysisResult:
        text = f"{note.name}\n{note.body}".lower()

        for pattern, query in self.QUERY_PATTERNS:
            if pattern in text:
                return AnalysisResult(
                    query=query,
                    rationale=f"Detected classroom language around {pattern}.",
                )

        query = self._fallback_query(text)
        return AnalysisResult(
            query=query,
            rationale="Using a fallback early-childhood behavior query derived from the note text.",
        )

    def summarize_work(self, work: dict[str, Any], note: StoredObservation, query: str) -> str:
        title = str(work.get("display_name") or work.get("title") or "Untitled work").strip()
        abstract = extract_abstract_text(work)
        if abstract:
            sentence = _first_sentence(abstract)
            if len(sentence.split()) > 36:
                sentence = _shorten_sentence(sentence, 36)
        else:
            sentence = (
                f"The paper '{title}' aligns with the note's theme of {query or 'toddler behavior'}."
            )

        return _one_sentence(
            f"{note.name} matched '{title}' for query '{query}' because {sentence}"
        )

    def summarize_pair(self, note: StoredObservation, query: str, works: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for work in works[:2]:
            title = str(work.get("display_name") or work.get("title") or "Untitled work").strip()
            abstract = extract_abstract_text(work)
            if abstract:
                sentence = _first_sentence(abstract)
                if len(sentence.split()) > 28:
                    sentence = _shorten_sentence(sentence, 28)
            else:
                sentence = f"The paper '{title}' aligns with the query theme of {query}."
            parts.append(f"{title}: {sentence}")

        if not parts:
            return _one_sentence(f"{note.name} had no OpenAlex works to summarize for query '{query}'.")

        joined = " | ".join(parts)
        return _one_sentence(f"{note.name} query '{query}' -> {joined}")

    @staticmethod
    def _fallback_query(text: str) -> str:
        if "peer" in text or "personal space" in text or "turn-taking" in text or "turn taking" in text:
            return "toddler peer boundaries turn taking"
        if "transition" in text:
            return "toddler transition support early childhood"
        if "frustration" in text or "bothered" in text or "escalated" in text:
            return "toddler frustration self regulation"
        if "voice" in text or "circle time" in text or "disrupt" in text:
            return "toddler classroom behavior regulation"
        return "early childhood behavior self regulation"


def _shorten_sentence(sentence: str, max_words: int) -> str:
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    return " ".join(words[:max_words]).rstrip(",;:") + "."


def append_trace_lines(trace_path: Path, lines: list[str]) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        for line in lines:
            if not line:
                continue
            handle.write(line.rstrip() + "\n")


def process_note(
    note: StoredObservation,
    analyzer: ToddlerBehaviorLLMWrapper,
    openalex: OpenAlexClient,
) -> tuple[list[str], AnalysisResult]:
    analysis = analyzer.deduce_query(note)
    note_id = getattr(note, "id", None)
    note_name = getattr(note, "name", "Unknown note")
    note_label = f"note {note_id}" if note_id is not None else note_name
    print(f"[trace] {note_label}: query -> {analysis.query}", flush=True)

    print("[trace] searching OpenAlex...", flush=True)
    search_result = openalex.search_works(
        topic_query=analysis.query,
        per_page=5,
        select="id,display_name,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_location,best_oa_location,open_access,has_content,ids",
    )
    candidates = search_result.get("results", [])
    print(f"[trace] OpenAlex returned {len(candidates)} candidate(s)", flush=True)
    if not candidates:
        line = _one_sentence(
            f"{note_name} triggered the query '{analysis.query}', but OpenAlex returned no works."
        )
        return [line], analysis

    selected_candidates = candidates[:2]
    print(f"[trace] using first {len(selected_candidates)} work(s) from query results", flush=True)
    for candidate in selected_candidates:
        work_id = (candidate.get("id") or "").rstrip("/").split("/")[-1]
        print(f"[trace] fetching work {work_id}", flush=True)
        if work_id:
            full_work = openalex.get_work(work_id)
            candidate.update(full_work)

    line = analyzer.summarize_pair(note, analysis.query, selected_candidates)
    return [line], analysis


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read notes from Ghost Build, search OpenAlex, and append trace summaries.")
    parser.add_argument("--ghost-state-path", type=Path, default=DEFAULT_GHOST_STATE_PATH)
    parser.add_argument("--ghost-database-name", default=DEFAULT_GHOST_DATABASE_NAME)
    parser.add_argument(
        "--ghost-database-id",
        default=None,
        help="Ghost Build database id to reuse if it exists; defaults to the stored state or env var.",
    )
    parser.add_argument("--trace-path", type=Path, default=DEFAULT_TRACE_PATH)
    parser.add_argument(
        "--note-file",
        type=Path,
        default=None,
        help="Bypass Ghost and process this local note file on every cycle.",
    )
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--single-shot", action="store_true", help="Process one available note and exit.")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Process 3 notes and exit so you can verify the end-to-end path quickly.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Maximum notes to process; 0 means run forever.")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    openalex_api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not openalex_api_key:
        print("error: OPENALEX_API_KEY is required", file=sys.stderr)
        return 1

    analyzer = ToddlerBehaviorLLMWrapper()
    openalex = OpenAlexClient(
        api_key=openalex_api_key,
        user_agent="monty-toddler-trace/0.1 (contact: local-runner)",
    )
    ghost_db = GhostBuildDatabase(args.ghost_database_name, args.ghost_state_path, args.ghost_database_id)

    smoke_test_limit = SMOKE_TEST_LIMIT if args.smoke_test else 0
    effective_limit = smoke_test_limit or (1 if args.single_shot else args.limit)
    processed = 0
    try:
        if args.note_file is None:
            ghost_db.initialize()
            print(
                f"[trace] polling all ingested notes every {args.interval_seconds:.1f}s; "
                f"writing to {args.trace_path}",
                flush=True,
            )
        else:
            print(
                f"[trace] processing {args.note_file} every {args.interval_seconds:.1f}s; "
                f"writing to {args.trace_path}",
                flush=True,
            )
        while True:
            if args.note_file is None:
                notes = ghost_db.read_notes(limit=None, order="asc")
                print(f"[trace] loaded {len(notes)} ghost note(s)", flush=True)
            else:
                notes = [parse_note_file(args.note_file)]

            if not notes:
                print("[trace] no notes found yet", flush=True)
            else:
                for note in notes:
                    lines, _analysis = process_note(note, analyzer, openalex)
                    append_trace_lines(args.trace_path, lines)
                    processed += 1
                    note_id = getattr(note, "id", None)
                    label = f"note {note_id}" if note_id is not None else note.name
                    print(f"[trace] {label} -> {len(lines)} line(s)", flush=True)

            if args.single_shot:
                break
            if effective_limit and processed >= effective_limit:
                break

            time.sleep(max(args.interval_seconds, 0.0))
    except (KeyboardInterrupt, BrokenPipeError):
        return 130
    except (HTTPError, URLError) as exc:
        print(f"error: OpenAlex request failed: {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, GhostBuildError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
