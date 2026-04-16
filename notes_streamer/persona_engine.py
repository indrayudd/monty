"""LLM-driven note generator conditioned on persona + recent context.

Replaces the static-corpus generator (scripts/generate_notes_corpus.py).
Called by the streamer on each tick, and by POST /api/persona/next-note.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PersonaOverrides:
    slider: float = 0.0           # -1.0 functional .. +1.0 dysfunctional
    flavor_override: str | None = None
    activity_weight: float = 1.0
    inject_next: str | None = None  # "neutral" | "problematic" | "emergency" | "surprise"
    interact_with: str | None = None
    interact_scene_hint: str | None = None


import frontmatter
from intelligence.api.services.wiki_paths import WIKI_ROOT


def list_personas() -> list[dict]:
    """Return persona summaries from wiki/personas/*.md."""
    personas_dir = WIKI_ROOT / "personas"
    out: list[dict] = []
    for path in sorted(personas_dir.glob("*.md")):
        post = frontmatter.load(path)
        out.append({
            "name": post.metadata.get("name", path.stem.replace("_", " ")),
            "age_band": post.metadata.get("age_band"),
            "temperament_axes": post.metadata.get("temperament_axes", {}),
            "dysfunction_flavor": post.metadata.get("dysfunction_flavor"),
            "recurring_companions": post.metadata.get("recurring_companions", []),
            "narrative": post.content.strip(),
            "file_path": str(path.relative_to(WIKI_ROOT)),
        })
    return out
