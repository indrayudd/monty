from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

_env_path = Path(__file__).resolve().parents[3] / "contracts" / ".env"
for line in _env_path.read_text().strip().splitlines():
    if line.startswith("OPENAI_API_KEY="):
        os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()

client = OpenAI()

SYSTEM_PROMPT = """You are an expert Montessori child behavioral analyst. You are given a SINGLE teacher observation note for a student. Analyze this one note and produce a behavioral assessment.

Return ONLY valid JSON with these exact keys:
{
  "profile_summary": "1-2 sentence assessment of the child's behavior in THIS observation",
  "behavioral_patterns": "key behaviors observed in this note, comma-separated",
  "severity": "green OR yellow OR red",
  "suggestions": "1-2 actionable recommendations for educators based on this observation"
}

Severity guide for a SINGLE observation:
- GREEN: The child was calm, focused, self-directed, and age-appropriate throughout. No adult intervention needed beyond normal guidance. Material handled respectfully, transitions smooth.
- YELLOW: Some difficulty observed — mild frustration, needed a reminder about voice/space/transitions, brief dysregulation that resolved with minimal support. The behavior is worth monitoring but not alarming.
- RED: Significant concern — repeated disruption, sustained dysregulation, peer conflict requiring intervention, escalation that affected the classroom, or persistent difficulty that required extended adult support.

Be decisive. A calm, focused work period is GREEN. A note mentioning frustration, reminders, or peer issues is YELLOW or RED depending on intensity and duration."""


QUERY_PROMPT = """You are an expert in early childhood education research, specifically Montessori pedagogy for toddlers and preschoolers (ages 2-6).

Given a student's aggregated behavioral profile from their Montessori classroom, generate exactly 2 targeted academic search queries for finding relevant research papers.

STRICT RULES for queries:
- Every query MUST include "toddler" or "preschool" AND "Montessori" or "early childhood classroom"
- Focus on the SPECIFIC behavioral pattern (e.g. "peer boundary", "transition difficulty", "turn-taking", "frustration tolerance") — not generic terms
- Use precise academic terminology: "executive function", "self-regulation", "prosocial behavior", "emotional dysregulation", "sensory processing", "work cycle engagement"
- Do NOT use vague terms like "strategies", "impact", "behavioral interventions" alone
- Queries should be 6-10 words, not full sentences

GOOD examples:
- "toddler Montessori peer conflict prosocial behavior"
- "preschool self-regulation frustration tolerance classroom"
- "toddler turn-taking executive function early childhood"
- "Montessori work cycle concentration preschool engagement"

BAD examples (too generic, will return off-topic papers):
- "self-regulation strategies in early childhood education"
- "impact of adult intervention on behavioral dysregulation"

Return ONLY valid JSON:
{
  "queries": ["query 1", "query 2"],
  "rationale": "Brief explanation"
}"""


def generate_search_queries(student_name: str, patterns: str, summary: str, severity: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": QUERY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Student: {student_name}\n"
                    f"Severity: {severity}\n"
                    f"Behavioral patterns: {patterns}\n"
                    f"Summary: {summary}"
                ),
            },
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def assess_note(student_name: str, note_body: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Student: {student_name}\n\nObservation Note:\n\n{note_body}"},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    result["student_name"] = student_name

    if result.get("severity") not in ("green", "yellow", "red"):
        result["severity"] = "yellow"

    return result
