from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
import time

from intelligence.api.services.ghost_client import (
    count_notes,
    ensure_agent_tables,
    ensure_notes_table,
    get_agent_actions,
    get_alerts,
    get_all_profiles,
    get_knowledge_graph_entries,
    get_personality_graph,
    get_recent_notes,
    get_runtime_state,
    insert_agent_action,
    insert_ingested_note,
    reset_agent_state,
    reset_notes_state,
)
from intelligence.api.services.self_improve import run_agent_cycle
from notes_streamer.note_parser import parse_note_file


NOTES_DIR = Path(__file__).resolve().parents[3] / "notes_streamer" / "notes"
NOTE_INTERVAL_SECONDS = 1.0
AGENT_INTERVAL_SECONDS = 2.0


@dataclass
class _RuntimeState:
    started: bool = False
    note_cursor: int = 0
    ingest_thread: Thread | None = None
    agent_thread: Thread | None = None
    stop_event: Event | None = None


_STATE = _RuntimeState()
_LOCK = Lock()


def _note_paths() -> list[Path]:
    return sorted(path for path in NOTES_DIR.glob("*.txt") if path.is_file())


def _next_note_path() -> Path | None:
    paths = _note_paths()
    if not paths:
        return None
    path = paths[_STATE.note_cursor % len(paths)]
    _STATE.note_cursor += 1
    return path


def _ingest_worker(stop_event: Event) -> None:
    while not stop_event.is_set():
        path = _next_note_path()
        if path is None:
            stop_event.wait(NOTE_INTERVAL_SECONDS)
            continue

        parsed = parse_note_file(path)
        inserted = insert_ingested_note(parsed.name, parsed.body)
        if inserted:
            insert_agent_action(
                {
                    "student_name": parsed.name,
                    "note_id": inserted["id"],
                    "action_kind": "note_ingested",
                    "status": "success",
                    "payload": {
                        "source_path": str(path),
                        "preview": " ".join(parsed.body.split())[:180],
                    },
                }
            )
        stop_event.wait(NOTE_INTERVAL_SECONDS)


def _agent_worker(stop_event: Event) -> None:
    while not stop_event.is_set():
        summary = run_agent_cycle(force_full=False, verbose=False)
        if summary.get("students_processed") or summary.get("new_knowledge_nodes") or summary.get("new_notes"):
            insert_agent_action(
                {
                    "student_name": None,
                    "note_id": None,
                    "action_kind": "cycle_summary",
                    "status": "success",
                    "payload": summary,
                }
            )
        stop_event.wait(AGENT_INTERVAL_SECONDS)


def _stop_threads_unlocked() -> None:
    stop_event = _STATE.stop_event
    if stop_event is not None:
        stop_event.set()
    if _STATE.ingest_thread is not None:
        _STATE.ingest_thread.join(timeout=2.0)
    if _STATE.agent_thread is not None:
        _STATE.agent_thread.join(timeout=2.0)
    _STATE.started = False
    _STATE.ingest_thread = None
    _STATE.agent_thread = None
    _STATE.stop_event = None


def bootstrap_demo(reset: bool = False) -> dict:
    with _LOCK:
        ensure_notes_table()
        ensure_agent_tables()

        if reset:
            _stop_threads_unlocked()
            reset_notes_state()
            reset_agent_state()
            _STATE.note_cursor = 0

        if not _STATE.started:
            stop_event = Event()
            _STATE.stop_event = stop_event
            _STATE.ingest_thread = Thread(target=_ingest_worker, args=(stop_event,), daemon=True, name="monty-demo-ingest")
            _STATE.agent_thread = Thread(target=_agent_worker, args=(stop_event,), daemon=True, name="monty-demo-agent")
            _STATE.ingest_thread.start()
            _STATE.agent_thread.start()
            _STATE.started = True

    return get_demo_overview()


def get_demo_overview() -> dict:
    profiles = get_all_profiles()
    selected_student = profiles[0]["student_name"] if profiles else None
    personality_graphs = {
        profile["student_name"]: get_personality_graph(profile["student_name"])
        for profile in profiles
    }
    knowledge_nodes = get_knowledge_graph_entries(limit=40)
    notes = get_recent_notes(limit=20)
    actions = get_agent_actions(limit=40)
    alerts = get_alerts(status=None, limit=20)

    return {
        "runtime": {
            "started": _STATE.started,
            "note_interval_seconds": NOTE_INTERVAL_SECONDS,
            "agent_interval_seconds": AGENT_INTERVAL_SECONDS,
            **get_runtime_state(),
        },
        "counts": {
            "notes": count_notes(),
            "profiles": len(profiles),
            "knowledge_nodes": len(knowledge_nodes),
            "alerts": len(alerts),
            "actions": len(actions),
        },
        "selected_student": selected_student,
        "students": profiles,
        "recent_notes": notes,
        "recent_actions": actions,
        "alerts": alerts,
        "knowledge_nodes": knowledge_nodes,
        "personality_graphs": personality_graphs,
        "timestamp": time.time(),
    }
