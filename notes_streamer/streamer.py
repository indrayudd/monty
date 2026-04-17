from __future__ import annotations

import random
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from notes_streamer.persona_engine import generate_next_note, PersonaOverrides, list_personas
from intelligence.api.services.ghost_client import (
    insert_observation,
    get_runtime_overrides,
)


def _pick_persona() -> dict:
    """Pick a persona weighted by activity_weight (default 1.0)."""
    personas = list_personas()
    overrides = get_runtime_overrides()
    weighted: list[tuple[dict, float]] = []
    for p in personas:
        block = overrides.get(p["name"], {})
        w = float(block.get("activity_weight", 1.0))
        if w <= 0:
            continue
        weighted.append((p, w))
    if not weighted:
        # All personas paused — fall back to picking at random anyway so the loop doesn't stall.
        return random.choice(personas)
    total = sum(w for _, w in weighted)
    r = random.uniform(0, total)
    upto = 0.0
    for p, w in weighted:
        upto += w
        if upto >= r:
            return p
    return weighted[-1][0]


def stream_one_note() -> None:
    """Generate and insert one persona-driven observation."""
    persona = _pick_persona()
    overrides_block = get_runtime_overrides().get(persona["name"], {})
    po = PersonaOverrides(
        slider=float(overrides_block.get("slider", 0.0)),
        flavor_override=overrides_block.get("flavor_override"),
        activity_weight=float(overrides_block.get("activity_weight", 1.0)),
        inject_next=overrides_block.get("inject_next"),
        interact_with=overrides_block.get("interact_with"),
        interact_scene_hint=overrides_block.get("interact_scene_hint"),
    )
    note = generate_next_note(persona["name"], overrides=po)
    insert_observation(name=note["name"], body=note["body"])
    print(f"[streamer] inserted note for {note['name']} (severity_hint={note['severity_hint']})", flush=True)

    # Clear one-shot fields so they don't repeat next tick.
    if overrides_block.get("inject_next") or overrides_block.get("interact_with"):
        from intelligence.api.services.ghost_client import set_runtime_overrides
        ov = get_runtime_overrides()
        block = ov.get(persona["name"], {})
        block.pop("inject_next", None)
        block.pop("interact_with", None)
        block.pop("interact_scene_hint", None)
        ov[persona["name"]] = block
        set_runtime_overrides(ov)


MAX_CONSECUTIVE_ERRORS = 10
RETRY_BACKOFF_SECONDS = 5.0


def main() -> int:
    print("[streamer] starting persona-driven note stream", flush=True)
    consecutive_errors = 0
    while True:
        try:
            stream_one_note()
            consecutive_errors = 0
            # Read cadence from god_mode_overrides (set via God Mode UI).
            # Default: random 2-8s. If _note_cadence is set, use that as
            # a fixed interval with ±20% jitter.
            try:
                ov = get_runtime_overrides()
                cadence = float(ov.get("_note_cadence", 0))
            except Exception:
                cadence = 0
            if cadence > 0:
                time.sleep(cadence * random.uniform(0.8, 1.2))
            else:
                time.sleep(random.uniform(2.0, 8.0))
        except (KeyboardInterrupt, BrokenPipeError):
            return 130
        except Exception as exc:
            consecutive_errors += 1
            print(
                f"[streamer] error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {exc}",
                file=sys.stderr,
                flush=True,
            )
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("[streamer] too many consecutive errors, exiting", file=sys.stderr, flush=True)
                return 1
            time.sleep(RETRY_BACKOFF_SECONDS)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
