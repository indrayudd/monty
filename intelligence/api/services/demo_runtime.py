from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
import time

from psycopg2 import OperationalError

from intelligence.api.services.ghost_client import (
    count_notes,
    delete_runtime_keys,
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
    set_runtime_values,
)
from intelligence.api.services.self_improve import run_agent_cycle
from notes_streamer.note_parser import parse_note_file


NOTES_DIR = Path(__file__).resolve().parents[3] / "notes_streamer" / "notes"
NOTE_INTERVAL_SECONDS = 1.0
AGENT_INTERVAL_SECONDS = 2.0


@dataclass
class _RuntimeState:
    started: bool = False
    mode: str = "idle"
    note_cursor: int = 0
    ingest_thread: Thread | None = None
    agent_thread: Thread | None = None
    stop_event: Event | None = None


_STATE = _RuntimeState()
_LOCK = Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_runtime_state(
    mode: str,
    *,
    started: bool,
    stage: str | None = None,
    student_name: str | None = None,
    note_id: int | None = None,
    message: str | None = None,
) -> None:
    _STATE.mode = mode
    _STATE.started = started
    payload: dict[str, object | None] = {
        "mode": mode,
        "demo_started": "1" if started else "0",
    }
    if stage is not None:
        payload["current_stage"] = stage
        payload["stage_started_at"] = _utcnow()
    if student_name is not None:
        payload["current_student"] = student_name
    if note_id is not None:
        payload["current_note_id"] = note_id
    if message is not None:
        payload["stage_message"] = message
    set_runtime_values(payload)


def _note_paths() -> list[Path]:
    return sorted(path for path in NOTES_DIR.glob("*.txt") if path.is_file())


def _next_note_path() -> Path | None:
    paths = _note_paths()
    if not paths or _STATE.note_cursor >= len(paths):
        return None
    path = paths[_STATE.note_cursor]
    _STATE.note_cursor += 1
    return path


def _ingest_worker(stop_event: Event) -> None:
    stop_event.wait(NOTE_INTERVAL_SECONDS)
    while not stop_event.is_set():
        path = _next_note_path()
        if path is None:
            _write_runtime_state(
                "running",
                started=True,
                stage="waiting_for_note",
                message="Waiting for the next note file to ingest.",
            )
            stop_event.wait(NOTE_INTERVAL_SECONDS)
            continue

        parsed = parse_note_file(path)
        _write_runtime_state(
            "running",
            started=True,
            stage="ingesting_note",
            student_name=parsed.name,
            message=f"Ingesting a classroom note for {parsed.name}.",
        )
        inserted = insert_ingested_note(parsed.name, parsed.body)
        if inserted:
            _write_runtime_state(
                "running",
                started=True,
                stage="note_ingested",
                student_name=parsed.name,
                note_id=int(inserted["id"]),
                message=f"Inserted note #{inserted['id']} for {parsed.name}.",
            )
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
    stop_event.wait(AGENT_INTERVAL_SECONDS)
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
    _STATE.ingest_thread = None
    _STATE.agent_thread = None
    _STATE.stop_event = None
    _write_runtime_state(
        "idle",
        started=False,
        stage="idle",
        message="Ready to start a fresh live demo.",
    )


def start_demo(reset: bool = False) -> dict:
    with _LOCK:
        ensure_notes_table()
        ensure_agent_tables()

        if reset:
            _write_runtime_state(
                "resetting",
                started=False,
                stage="resetting",
                message="Clearing notes, profiles, and graph state.",
            )
            _stop_threads_unlocked()
            reset_notes_state()
            reset_agent_state()
            _STATE.note_cursor = 0

        if not _STATE.started:
            stop_event = Event()
            _STATE.stop_event = stop_event
            _write_runtime_state(
                "running",
                started=True,
                stage="waiting_for_note",
                message="Live demo started. Waiting for the first classroom observation.",
            )
            _STATE.ingest_thread = Thread(target=_ingest_worker, args=(stop_event,), daemon=True, name="monty-demo-ingest")
            _STATE.agent_thread = Thread(target=_agent_worker, args=(stop_event,), daemon=True, name="monty-demo-agent")
            _STATE.ingest_thread.start()
            _STATE.agent_thread.start()
        else:
            _write_runtime_state(
                "running",
                started=True,
                stage="waiting_for_note",
                message="Live demo already running.",
            )

    return get_demo_overview()


def reset_demo() -> dict:
    with _LOCK:
        ensure_notes_table()
        ensure_agent_tables()
        _write_runtime_state(
            "resetting",
            started=False,
            stage="resetting",
            message="Clearing notes, profiles, and graph state.",
        )
        _stop_threads_unlocked()
        reset_notes_state()
        reset_agent_state()
        _STATE.note_cursor = 0
        set_runtime_values(
            {
                "mode": "idle",
                "demo_started": "0",
                "current_stage": "idle",
                "stage_started_at": _utcnow(),
                "stage_message": "Ready to start a fresh live demo.",
                "current_student": "",
                "current_note_id": "",
            }
        )
        delete_runtime_keys(["last_processed_note_id", "last_cycle_at", "last_cycle_student_count"])
        _STATE.mode = "idle"
        _STATE.started = False

    return get_demo_overview()


def stop_demo() -> dict:
    with _LOCK:
        if _STATE.started:
            _stop_threads_unlocked()
        set_runtime_values(
            {
                "mode": "stopped",
                "demo_started": "0",
                "current_stage": "idle",
                "stage_started_at": _utcnow(),
                "stage_message": "Live demo stopped. Start again to replay from the current state or reset first.",
                "current_student": "",
                "current_note_id": "",
            }
        )
        _STATE.mode = "stopped"
        _STATE.started = False

    return get_demo_overview()


def bootstrap_demo(reset: bool = False) -> dict:
    return start_demo(reset=reset)


def _empty_overview(runtime: dict, *, stage_message: str, error: str | None = None) -> dict:
    runtime["current_stage"] = runtime.get("current_stage") or "idle"
    runtime["stage_message"] = stage_message
    runtime["current_student"] = runtime.get("current_student") or ""
    runtime["current_note_id"] = runtime.get("current_note_id") or ""
    if error:
        runtime["data_status"] = "degraded"
        runtime["last_error"] = error
    return {
        "runtime": runtime,
        "counts": {
            "notes": 0,
            "profiles": 0,
            "knowledge_nodes": 0,
            "alerts": 0,
            "actions": 0,
        },
        "selected_student": None,
        "students": [],
        "recent_notes": [],
        "recent_actions": [],
        "alerts": [],
        "knowledge_nodes": [],
        "personality_graphs": {},
        "timestamp": time.time(),
    }


def get_demo_overview() -> dict:
    runtime_state = get_runtime_state()
    started = _STATE.started
    mode = _STATE.mode if _STATE.mode else ("running" if started else "idle")
    runtime = {
        **runtime_state,
        "started": started,
        "note_interval_seconds": NOTE_INTERVAL_SECONDS,
        "agent_interval_seconds": AGENT_INTERVAL_SECONDS,
    }
    runtime["mode"] = mode

    if not started:
        return _empty_overview(runtime, stage_message="Ready to start a fresh live demo.")

    try:
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
        notes_count = count_notes()
    except OperationalError as exc:
        message = runtime.get("stage_message") or "Live demo is running, but data is temporarily unavailable. Retrying."
        return _empty_overview(runtime, stage_message=str(message), error=str(exc))

    return {
        "runtime": runtime,
        "counts": {
            "notes": notes_count,
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
