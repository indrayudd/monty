"""LLM-driven note generator conditioned on persona + recent context.

Replaces the static-corpus generator (scripts/generate_notes_corpus.py).
Called by the streamer on each tick, and by POST /api/persona/next-note.

This module is a stub in Phase 0. Full implementation in Phase 1.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaOverrides:
    slider: float = 0.0           # -1.0 functional .. +1.0 dysfunctional
    flavor_override: str | None = None
    activity_weight: float = 1.0
    inject_next: str | None = None  # "neutral" | "problematic" | "emergency" | "surprise"
    interact_with: str | None = None
    interact_scene_hint: str | None = None


def generate_next_note(student_name: str, overrides: PersonaOverrides | None = None) -> dict:
    """Return {name, body, severity_hint}. Caller inserts into ingested_observations."""
    raise NotImplementedError("persona_engine.generate_next_note — implement in Phase 1")


def list_personas() -> list[dict]:
    """Return persona summaries from wiki/personas/*.md including current overrides."""
    raise NotImplementedError("persona_engine.list_personas — implement in Phase 1")
