"""LLM-driven note generator conditioned on persona + recent context.

Replaces the static-corpus generator (scripts/generate_notes_corpus.py).
Called by the streamer on each tick, and by POST /api/persona/next-note.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import frontmatter
from intelligence.api.services.wiki_paths import WIKI_ROOT


@dataclass
class PersonaOverrides:
    slider: float = 0.0           # -1.0 functional .. +1.0 dysfunctional
    flavor_override: str | None = None
    activity_weight: float = 1.0
    inject_next: str | None = None  # "neutral" | "problematic" | "emergency" | "surprise"
    interact_with: str | None = None
    interact_scene_hint: str | None = None


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


from openai import OpenAI

from intelligence.api.services.ghost_client import (
    list_student_incidents,
)


def _openai_client() -> OpenAI | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    return OpenAI(api_key=key)


def _persona_block(student_name: str) -> dict | None:
    for p in list_personas():
        if p["name"] == student_name:
            return p
    return None


def _recent_own_incidents(student_name: str, limit: int = 3) -> list[str]:
    """Return recent incident body texts for this student. Empty list if none."""
    incidents = list_student_incidents(student_name, limit=limit)
    out: list[str] = []
    for inc in incidents:
        try:
            text = Path(inc["file_path"]).read_text(encoding="utf-8")
            # Just include the body markdown, not the YAML frontmatter
            if "---" in text:
                _, _, body = text.partition("---")
                _, _, body = body.partition("---")
                out.append(body.strip()[:600])
            else:
                out.append(text[:600])
        except Exception:
            continue
    return out


def _recent_companion_incidents(persona: dict, limit: int = 3) -> list[str]:
    """Return recent incidents involving recurring companions."""
    out: list[str] = []
    for companion in persona.get("recurring_companions", []):
        out.extend(_recent_own_incidents(companion, limit=1))
        if len(out) >= limit:
            break
    return out[:limit]


def generate_next_note(
    student_name: str, overrides: PersonaOverrides | None = None
) -> dict:
    """Return {name, body, severity_hint}. Caller inserts into ingested_observations."""
    overrides = overrides or PersonaOverrides()
    persona = _persona_block(student_name)
    if not persona:
        raise ValueError(f"no persona found for {student_name}")

    own = _recent_own_incidents(student_name)
    companions = _recent_companion_incidents(persona)

    # If God Mode injected a one-shot directive, it overrides slider behavior.
    inject = overrides.inject_next

    # Translate slider to qualitative band the LLM can use.
    s = overrides.slider
    band = (
        "deeply normalized and concentrated" if s < -0.6
        else "settled and engaged" if s < -0.2
        else "ordinary and mixed" if s < 0.2
        else "frayed and emotionally close to the surface" if s < 0.6
        else "acutely dysregulated, near-emergency"
    )
    flavor = overrides.flavor_override or persona.get("dysfunction_flavor", "scattered")

    interaction_clause = ""
    if overrides.interact_with:
        interaction_clause = (
            f"\n\nThis observation must include {overrides.interact_with} as a peer "
            f"in a meaningful interaction"
            f"{(' — scene hint: ' + overrides.interact_scene_hint) if overrides.interact_scene_hint else ''}."
        )

    inject_clause = ""
    severity_hint = "neutral"
    if inject == "neutral":
        inject_clause = "\n\nThis specific observation should be a quiet, neutral, normalized work-cycle moment regardless of the slider state."
        severity_hint = "green"
    elif inject == "problematic":
        inject_clause = "\n\nThis specific observation must show a clear behavioral concern that needed adult intervention."
        severity_hint = "yellow"
    elif inject == "emergency":
        inject_clause = (
            "\n\nThis specific observation must be an EMERGENCY — explicit threats, "
            "self-harm language, or movement toward weapons or peers in a way that required "
            "two adults to contain. Use unambiguous language so the agent's emergency triggers fire."
        )
        severity_hint = "red"
    elif inject == "surprise":
        inject_clause = "\n\nThis specific observation should surprise the reader — go against the established pattern in this child's recent notes in a plausible way."
        severity_hint = "yellow"

    own_block = "\n---\n".join(own) if own else "(no prior observations for this child yet)"
    comp_block = "\n---\n".join(companions) if companions else "(no recent peer-context available)"

    system = (
        "You are an experienced Montessori guide writing a single classroom observation note "
        "about one specific child. Notes are 2-3 short paragraphs of natural prose. They begin "
        "with 'Name: <child full name>' on its own line, then a blank line, then the observation. "
        "Use real Montessori vocabulary (work cycle, presentation, normalization, sensorial, "
        "practical life, moveable alphabet, transitions). Do NOT add headings, bullets, "
        "interpretation, plans, or commentary outside the observation itself. Do NOT mention "
        "previous notes or the agent watching."
    )

    user = f"""Write one observation note for the following child.

PERSONA:
Name: {persona['name']}
Age band: {persona['age_band']}
Dysfunction flavor (when stressed): {flavor}
Persona narrative:
{persona['narrative']}

CURRENT REGULATORY STATE: this child is currently {band}.

RECENT OBSERVATIONS OF THIS CHILD (most recent first, may be empty):
{own_block}

RECENT OBSERVATIONS INVOLVING RECURRING COMPANIONS:
{comp_block}
{interaction_clause}{inject_clause}

Output exactly the note in the format:

Name: {persona['name']}

<observation paragraphs>
"""

    def _fallback_body() -> str:
        return (
            f"Name: {persona['name']}\n\n"
            f"{persona['name']} chose a familiar work and proceeded with steady attention. "
            f"The child maintained a calm body and used the material respectfully throughout the cycle. "
            f"By the end of the observation the child had returned the material to the shelf in order.\n"
        )

    client = _openai_client()
    if client is None:
        # Fallback: cheap deterministic template so the demo doesn't break without an API key.
        # Preserve severity_hint from inject directive even in fallback.
        return {"name": persona['name'], "body": _fallback_body(), "severity_hint": severity_hint if inject else "green"}

    try:
        resp = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.9,
            max_tokens=400,
        )
        body = resp.choices[0].message.content.strip()
        if not body.startswith("Name:"):
            body = f"Name: {persona['name']}\n\n{body}"
        return {"name": persona["name"], "body": body + ("\n" if not body.endswith("\n") else ""), "severity_hint": severity_hint}
    except Exception:
        # API unavailable / quota exhausted — fall back to deterministic template.
        # Preserve severity_hint from inject directive even in fallback.
        return {"name": persona['name'], "body": _fallback_body(), "severity_hint": severity_hint if inject else "green"}
