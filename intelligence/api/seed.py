"""Run this to seed student profiles from notes. Separate from the API server."""
from __future__ import annotations

from collections import defaultdict

from intelligence.api.services.ghost_client import (
    get_all_notes,
    insert_snapshot,
    upsert_student_profile,
)
from intelligence.api.services.llm_service import assess_note


def run():
    notes = get_all_notes()
    print(f"Found {len(notes)} notes. Assessing each one...\n")

    student_state: dict[str, dict] = defaultdict(lambda: {"count": 0, "prev_severity": None})

    for i, note in enumerate(notes, 1):
        name = note["name"]
        print(f"[{i}/{len(notes)}] {name} (note #{note['id']}) ... ", end="", flush=True)

        snapshot = assess_note(name, note["body"])
        snapshot["note_id"] = note["id"]

        insert_snapshot(snapshot)

        state = student_state[name]
        state["count"] += 1
        upsert_student_profile(name, snapshot, state["prev_severity"], state["count"])
        state["prev_severity"] = snapshot["severity"]

        print(f"-> {snapshot['severity']}")

    print(f"\nDone. {len(notes)} snapshots across {len(student_state)} students.")


if __name__ == "__main__":
    run()
