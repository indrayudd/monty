"""Quantifiable curiosity score + research-firing gate.

Six signals: novelty, recurrence_gap, cross_student, surprise,
severity_weight, recency. Composite score in [0, 1]. Gate fires research
when score >= 0.70 and 30-min cooldown elapsed.

This module is a stub in Phase 0. Full implementation in Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_WEIGHTS = {
    "novelty": 0.20,
    "recurrence_gap": 0.20,
    "cross_student": 0.20,
    "surprise": 0.15,
    "severity_weight": 0.15,
    "recency": 0.10,
}

CURIOSITY_THRESHOLD = 0.70
COOLDOWN_MINUTES = 30


@dataclass
class CuriosityFactors:
    novelty: float
    recurrence_gap: float
    cross_student: float
    surprise: float
    severity_weight: float
    recency: float

    def score(self, weights: dict[str, float] = DEFAULT_WEIGHTS) -> float:
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


def compute_factors(node_slug: str, recent_evidence_text: str | None = None) -> CuriosityFactors:
    raise NotImplementedError("curiosity.compute_factors — implement in Phase 3")


def evaluate_gate(node_slug: str) -> dict:
    """Return {fire: bool, score: float, factors: dict, reason: str}."""
    raise NotImplementedError("curiosity.evaluate_gate — implement in Phase 3")
