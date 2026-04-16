"""Quantifiable curiosity score + research-firing gate.

Six signals: novelty, recurrence_gap, cross_student, surprise,
severity_weight, recency. Composite score in [0, 1]. Gate fires research
when score >= 0.70 and 30-min cooldown elapsed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import frontmatter
import psycopg2.extras

from intelligence.api.services.ghost_client import (
    _agent_db_url,  # noqa: F401 — used via _conn
    get_runtime_overrides,
)
from intelligence.api.services.wiki_paths import BEHAVIORAL_TYPES, WIKI_ROOT


# ---------------------------------------------------------------------------
# Helpers imported locally to avoid circular-import with ghost_client
# ---------------------------------------------------------------------------

def _conn(url: str):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=5)


def _db():
    from intelligence.api.services.ghost_client import _agent_db_url as _u
    return _conn(_u())


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "novelty": 0.20,
    "recurrence_gap": 0.20,
    "cross_student": 0.20,
    "surprise": 0.15,
    "severity_weight": 0.15,
    "recency": 0.10,
}

CURIOSITY_THRESHOLD = 0.70
COOLDOWN_MINUTES = 30


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class CuriosityFactors:
    novelty: float
    recurrence_gap: float
    cross_student: float
    surprise: float
    severity_weight: float
    recency: float

    def score(self, weights: dict[str, float] | None = None) -> float:
        if weights is None:
            weights = DEFAULT_WEIGHTS
        return (
            weights["novelty"] * self.novelty
            + weights["recurrence_gap"] * self.recurrence_gap
            + weights["cross_student"] * self.cross_student
            + weights["surprise"] * self.surprise
            + weights["severity_weight"] * self.severity_weight
            + weights["recency"] * self.recency
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "novelty": self.novelty,
            "recurrence_gap": self.recurrence_gap,
            "cross_student": self.cross_student,
            "surprise": self.surprise,
            "severity_weight": self.severity_weight,
            "recency": self.recency,
        }


# ---------------------------------------------------------------------------
# Internal math
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _find_node_path(slug: str):
    """slug may be 'antecedents/peer-takes-material' or just 'peer-takes-material'."""
    if "/" in slug:
        ntype, name = slug.split("/", 1)
        candidate = WIKI_ROOT / "behavioral" / ntype / f"{name}.md"
        return candidate if candidate.exists() else None
    for ntype in BEHAVIORAL_TYPES:
        candidate = WIKI_ROOT / "behavioral" / ntype / f"{slug}.md"
        if candidate.exists():
            return candidate
    return None


def _recent_severity_for_node(slug_full: str) -> float:
    """Return max severity (red=1.0, yellow=0.5, green=0.0) of recent incidents touching this node."""
    sev_map = {"red": 1.0, "yellow": 0.5, "green": 0.0}
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT severity FROM student_incidents "
                    "WHERE %s = ANY(behavioral_ref_slugs) "
                    "ORDER BY ingested_at DESC LIMIT 5",
                    (f"behavioral/{slug_full}",),
                )
                rows = cur.fetchall()
        return max((sev_map.get(row["severity"], 0.0) for row in rows), default=0.0)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Public API — Task 3.1
# ---------------------------------------------------------------------------

def compute_factors(node_slug: str, recent_evidence_text: str | None = None) -> CuriosityFactors:
    """Compute all 6 factors for a behavioral node, given its current wiki state."""
    path = _find_node_path(node_slug)
    if path is None:
        # Unknown node — minimal defaults
        return CuriosityFactors(
            novelty=1.0, recurrence_gap=0.0, cross_student=0.0,
            surprise=0.0, severity_weight=0.0, recency=0.0,
        )

    post = frontmatter.load(path)
    meta = post.metadata
    support_count = int(meta.get("support_count", 0))
    students_count = int(meta.get("students_count", 0))
    literature_refs = int(meta.get("literature_refs", 0))

    novelty = 1.0 / (1.0 + literature_refs)
    recurrence_gap = _sigmoid(support_count - 3.0 * literature_refs)
    cross_student = _sigmoid(students_count - 2.0)

    # +0.20 first-crossing-of-3 bump, decayed back over 6 hours
    if students_count == 3 and meta.get("_first_crossed_3_at") is None:
        meta["_first_crossed_3_at"] = datetime.now(timezone.utc).isoformat()
        # Persist this stamp on next write — we don't write here directly.
        cross_student = min(1.0, cross_student + 0.20)
    elif meta.get("_first_crossed_3_at"):
        try:
            t0 = datetime.fromisoformat(meta["_first_crossed_3_at"])
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=timezone.utc)
            hours = (datetime.now(timezone.utc) - t0).total_seconds() / 3600.0
            bump = max(0.0, 0.20 * math.exp(-hours / 6.0))
            cross_student = min(1.0, cross_student + bump)
        except Exception:
            pass

    # Surprise: simple heuristic — token-overlap distance between new evidence and existing summary
    surprise = 0.0
    if recent_evidence_text:
        existing_summary = ""
        if "## Summary" in post.content:
            existing_summary = post.content.split("## Summary", 1)[1].split("##", 1)[0].lower()
        new_tokens = set(recent_evidence_text.lower().split())
        old_tokens = set(existing_summary.split())
        if new_tokens:
            shared = len(new_tokens & old_tokens) / len(new_tokens)
            surprise = max(0.0, 1.0 - shared)

    # Build the slug_full used to query incidents
    node_type = meta.get("type", "")
    node_slug_raw = meta.get("slug", node_slug.split("/")[-1])
    if "/" in node_slug:
        slug_full = node_slug
    elif node_type:
        slug_full = f"{node_type}/{node_slug_raw}"
    else:
        slug_full = node_slug_raw

    severity_weight = _recent_severity_for_node(slug_full)

    last_obs = meta.get("last_observed_at")
    recency = 0.0
    if last_obs:
        try:
            t = datetime.fromisoformat(str(last_obs))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            hours = (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
            recency = math.exp(-hours / 24.0)
        except Exception:
            pass

    return CuriosityFactors(
        novelty=round(novelty, 3),
        recurrence_gap=round(recurrence_gap, 3),
        cross_student=round(cross_student, 3),
        surprise=round(surprise, 3),
        severity_weight=round(severity_weight, 3),
        recency=round(recency, 3),
    )


# ---------------------------------------------------------------------------
# Public API — Task 3.2
# ---------------------------------------------------------------------------

def _current_weights() -> dict[str, float]:
    try:
        overrides = get_runtime_overrides()
        custom = overrides.get("_curiosity_weights") or {}
        weights = dict(DEFAULT_WEIGHTS)
        for k, v in custom.items():
            if k in weights and isinstance(v, (int, float)):
                weights[k] = float(v)
        return weights
    except Exception:
        return dict(DEFAULT_WEIGHTS)


def _last_research_at(node_slug: str):
    slug = node_slug.split("/")[-1]
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT last_research_fetched_at FROM behavioral_nodes WHERE slug = %s",
                    (slug,),
                )
                row = cur.fetchone()
                return row["last_research_fetched_at"] if row else None
    except Exception:
        return None


def evaluate_gate(node_slug: str) -> dict:
    """Return {fire: bool, score: float, factors: dict, reason: str, weights: dict}."""
    factors = compute_factors(node_slug)
    weights = _current_weights()
    score = factors.score(weights)

    last = _last_research_at(node_slug)
    cooldown_active = False
    if last:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = datetime.now(timezone.utc) - last
        cooldown_active = elapsed < timedelta(minutes=COOLDOWN_MINUTES)

    fire = (score >= CURIOSITY_THRESHOLD) and (not cooldown_active)
    reason = (
        "score below threshold" if score < CURIOSITY_THRESHOLD
        else "cooldown active" if cooldown_active
        else "fire"
    )

    # Persist event row for the audit log surfaced in /console.
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO curiosity_events (node_slug, fired_at, curiosity_score, factors, "
                    "triggered_research, paper_count) VALUES (%s, NOW(), %s, %s, %s, 0)",
                    (node_slug, score, psycopg2.extras.Json(factors.to_dict()), fire),
                )
                conn.commit()
    except Exception as exc:
        # Don't let DB errors block callers
        import logging
        logging.getLogger(__name__).warning("curiosity_events insert failed: %s", exc)

    return {
        "fire": fire,
        "score": round(score, 3),
        "factors": factors.to_dict(),
        "reason": reason,
        "weights": weights,
    }
