from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

from openai import OpenAI


_CLIENT: OpenAI | None = None

_ENV_PATHS = [
    Path(__file__).resolve().parents[3] / ".env",
    Path(__file__).resolve().parents[3] / "contracts" / ".env",
]

for env_path in _ENV_PATHS:
    if not env_path.exists():
        continue
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, _, val = line.partition("=")
        if key.strip() and val.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()


SYSTEM_PROMPT = """You are an expert Montessori child behavioral analyst. You are given a SINGLE teacher observation note for a student. Analyze this one note and produce a behavioral assessment.

Return ONLY valid JSON with these exact keys:
{
  "profile_summary": "1-2 sentence assessment of the child's behavior in THIS observation",
  "behavioral_patterns": "key behaviors observed in this note, comma-separated",
  "severity": "green OR yellow OR red",
  "suggestions": "1-2 actionable recommendations for educators based on this observation",
  "behavioral_nodes": [...],
  "behavioral_edges": [...],
  "peers_present": [...],
  "educator": "...",
  "slug_hint": "2-4 word description of this incident"
}

Severity guide for a SINGLE observation:
- GREEN: The child was calm, focused, self-directed, and age-appropriate throughout. No adult intervention needed beyond normal guidance. Material handled respectfully, transitions smooth.
- YELLOW: Some difficulty observed — mild frustration, needed a reminder about voice/space/transitions, brief dysregulation that resolved with minimal support. The behavior is worth monitoring but not alarming.
- RED: Significant concern — repeated disruption, sustained dysregulation, peer conflict requiring intervention, escalation that affected the classroom, or persistent difficulty that required extended adult support.

If the note contains violent threats, weapon language, self-harm language, or imminent danger, mark severity RED.

After your assessment, decompose this observation into a behavioral knowledge graph using the ABC + SEAT + BrainState taxonomy. Return a `behavioral_nodes` array and a `behavioral_edges` array in the JSON.

Allowed node types (use these exact strings): "setting_events", "antecedents", "behaviors", "functions", "brain_states", "responses", "protective_factors".

Allowed edge relations (use these exact strings): "predisposes", "amplifies", "triggers", "serves", "occurs_in", "gates", "follows", "reinforces", "extinguishes", "co-regulates", "evidences", "undermines", "recurs_with".

For each node, return: {"type": <node_type>, "slug": <kebab-case>, "title": <short title>, "summary": <one-sentence anonymized definition>, "evidence": <one anonymized sentence about THIS observation, no names, no dates, no times, no ages above "3-4" / "4-5" bands>}.

For each edge, return: {"src_type": ..., "src_slug": ..., "rel": ..., "dst_type": ..., "dst_slug": ..., "evidence": <anonymized one-liner>}.

CRITICAL: evidence strings MUST NOT contain student names, educator names, peer names, dates, or specific times. Phrasing like "a 3-4 year old", "a peer", "the guide" is required. The behavioral graph is anonymized; violations will be rejected by an automated lint.

peers_present should be the actual names of peers mentioned in the note (these are stored in the incident file, not in the anonymized behavioral graph). educator should be the educator name if present in the note. slug_hint should be 2-4 words describing this incident in kebab-friendly phrasing."""


HISTORY_PROMPT = """You are an expert Montessori child behavioral analyst. You are given a student's FULL recent note history, not a single observation. Re-assess the student using the accumulated evidence.

Return ONLY valid JSON:
{
  "profile_summary": "2-3 sentence summary of the current behavioral picture across the note history",
  "behavioral_patterns": "comma-separated list of recurring patterns",
  "severity": "green OR yellow OR red",
  "suggestions": "3 concrete educator actions tailored to the current pattern",
  "personality_traits": ["3 short phrases"],
  "regulation_triggers": ["3 short phrases"],
  "support_strategies": ["3 short phrases"],
  "knowledge_gaps": ["2 short research questions or missing knowledge areas"],
  "alert_reason": "short sentence",
  "emergency_action_required": true
}

Rules:
- Weight the full history, but pay extra attention to the most recent notes.
- If the history contains violent threats, weapon grabbing, shooting language, stabbing language, or self-harm threats, the student must be RED and emergency_action_required must be true.
- personality_traits should describe enduring classroom tendencies, not diagnoses.
- regulation_triggers should capture predictable contexts that precede escalation.
- support_strategies should be teacher-facing and action oriented.
- knowledge_gaps should be specific enough to drive academic paper search.
"""


QUERY_PROMPT = """You are an expert in early childhood education research, specifically Montessori pedagogy for toddlers and preschoolers (ages 2-6).

Given a student's aggregated behavioral profile from their Montessori classroom, generate exactly 2 targeted academic search queries for finding relevant research papers.

STRICT RULES for queries:
- Every query MUST include "toddler" or "preschool" AND "Montessori" or "early childhood classroom"
- Focus on the SPECIFIC behavioral pattern (e.g. "peer boundary", "transition difficulty", "turn-taking", "frustration tolerance") — not generic terms
- Use precise academic terminology: "executive function", "self-regulation", "prosocial behavior", "emotional dysregulation", "sensory processing", "work cycle engagement"
- Do NOT use vague terms like "strategies", "impact", "behavioral interventions" alone
- Queries should be 6-10 words, not full sentences

Return ONLY valid JSON:
{
  "queries": ["query 1", "query 2"],
  "rationale": "Brief explanation"
}"""


RESEARCH_SUMMARY_PROMPT = """You are helping a Montessori classroom safety and support agent turn research papers into small knowledge graph entries.

Return ONLY valid JSON:
{
  "insights": ["2 concise actionable insights"],
  "related_topics": ["2 concise related topics"],
  "confidence": 0.0
}

Rules:
- Focus on early childhood classroom practice.
- Insights must be plain-language and action-relevant.
- Confidence must be between 0.4 and 0.95.
"""


EMERGENCY_KEYWORDS = (
    "kill",
    "killing",
    "stab",
    "stabbing",
    "shoot",
    "shooting",
    "hurt myself",
    "hurt himself",
    "hurt herself",
    "hurt themselves",
    "weapon",
    "scissors",
)


def _get_client() -> OpenAI | None:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        return None
    _CLIENT = OpenAI()
    return _CLIENT


def _contains_emergency_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in EMERGENCY_KEYWORDS)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def _split_patterns(text: str) -> list[str]:
    return _dedupe(part.strip() for part in re.split(r"[,\n;]", text) if part.strip())


def _fallback_patterns(note_body: str) -> list[str]:
    lowered = note_body.lower()
    patterns: list[str] = []
    mapping = {
        "violent threat": ("kill", "stab", "shoot", "weapon"),
        "self-harm risk": ("hurt myself", "hurt herself", "hurt himself", "hurt themselves"),
        "transition difficulty": ("transition",),
        "peer boundary conflict": ("peer", "classmate", "space", "turn-taking"),
        "voice dysregulation": ("shout", "yell", "voice", "scream"),
        "frustration tolerance": ("frustrat", "push", "sharp", "angry"),
        "work cycle avoidance": ("restless", "between materials", "without completing"),
        "focused independent work": ("calm", "focused", "steady", "independent"),
    }
    for label, cues in mapping.items():
        if any(cue in lowered for cue in cues):
            patterns.append(label)
    return patterns or ["classroom behavior monitoring"]


def _fallback_note_assessment(student_name: str, note_body: str) -> dict:
    patterns = _fallback_patterns(note_body)
    emergency = _contains_emergency_language(note_body)
    lowered = note_body.lower()

    if emergency:
        severity = "red"
    elif any(token in lowered for token in ("intervene", "dysregulated", "peer", "reminder", "frustrat")):
        severity = "yellow"
    else:
        severity = "green"

    if emergency:
        summary = (
            f"{student_name} displayed acute safety-risk behavior in this observation, including violent or self-harm language "
            "that requires immediate escalation and direct adult containment."
        )
        suggestions = (
            "Move immediately into a safety response, keep constant adult supervision, and document a same-day family/admin follow-up."
        )
    elif severity == "yellow":
        summary = (
            f"{student_name} showed a meaningful regulation difficulty in this observation that disrupted the work cycle but remained containable with adult support."
        )
        suggestions = "Pre-correct the transition, reduce demands in the moment, and follow with a brief regulation reset before re-entry."
    else:
        summary = f"{student_name} remained regulated, focused, and able to participate appropriately in the Montessori work cycle."
        suggestions = "Continue the current level of independence support and reinforce the calm routine already working."

    return {
        "student_name": student_name,
        "profile_summary": summary,
        "behavioral_patterns": ", ".join(patterns),
        "severity": severity,
        "suggestions": suggestions,
    }


def _fallback_history_assessment(student_name: str, notes: list[dict]) -> dict:
    combined = "\n".join(note["body"] for note in notes)
    lowered = combined.lower()
    emergency = _contains_emergency_language(combined)
    problematic_count = sum(
        1 for note in notes if any(word in note["body"].lower() for word in ("intervene", "reminder", "frustrat", "peer", "dysreg"))
    )
    violent_count = sum(1 for note in notes if _contains_emergency_language(note["body"]))

    if emergency or violent_count:
        severity = "red"
    elif problematic_count >= max(3, len(notes) // 3):
        severity = "yellow"
    else:
        severity = "green"

    patterns = _dedupe(
        _fallback_patterns(combined)
        + (["recurrent high-risk aggression"] if violent_count else [])
    )

    personality_traits: list[str] = []
    if "focused independent work" in patterns:
        personality_traits.append("capable of sustained independent work when regulated")
    if "transition difficulty" in patterns:
        personality_traits.append("becomes unsettled when routines shift quickly")
    if "peer boundary conflict" in patterns:
        personality_traits.append("needs close scaffolding around peers and shared space")
    if emergency:
        personality_traits.append("can escalate rapidly from frustration into safety risk")
    if not personality_traits:
        personality_traits.append("shows variable classroom regulation across the observation set")

    regulation_triggers = _dedupe(
        [
            "busy transitions" if "transition difficulty" in patterns else "",
            "peer proximity" if "peer boundary conflict" in patterns else "",
            "frustration with task failure" if "frustration tolerance" in patterns else "",
            "acute threat language and access to objects" if emergency else "",
        ]
    ) or ["unstructured classroom moments"]

    support_strategies = _dedupe(
        [
            "front-load transition warnings and simplify re-entry expectations",
            "use immediate co-regulation and low-language boundary setting",
            "separate from peers and remove unsafe objects during escalation" if emergency else "",
            "schedule adult check-ins before high-risk parts of the work cycle",
        ]
    )

    knowledge_gaps = _dedupe(
        [
            "Montessori toddler aggression de-escalation" if emergency else "",
            "preschool self-regulation during transitions",
            "early childhood classroom peer boundary interventions",
        ]
    )[:2]

    if emergency:
        alert_reason = "Emergency note history includes violent or self-harm language."
    elif severity == "yellow":
        alert_reason = "Repeated dysregulation patterns justify monitoring and support refinement."
    else:
        alert_reason = "Current history is mostly stable with low acute concern."

    summary = (
        f"{student_name} has {len(notes)} notes on record. The recent history shows {', '.join(patterns[:4])}. "
        f"The current risk level is {severity} based on cumulative evidence rather than a single note."
    )
    suggestions = " | ".join(support_strategies[:3])

    return {
        "student_name": student_name,
        "profile_summary": summary,
        "behavioral_patterns": ", ".join(patterns[:6]),
        "severity": severity,
        "suggestions": suggestions,
        "personality_traits": personality_traits[:3],
        "regulation_triggers": regulation_triggers[:3],
        "support_strategies": support_strategies[:3],
        "knowledge_gaps": knowledge_gaps,
        "alert_reason": alert_reason,
        "emergency_action_required": emergency,
    }


def _fallback_queries(patterns: str, summary: str, emergency: bool) -> dict:
    lowered = f"{patterns} {summary}".lower()
    if emergency or any(term in lowered for term in ("violent", "kill", "stab", "shoot", "self-harm")):
        queries = [
            "preschool Montessori aggression de escalation classroom",
            "toddler early childhood self regulation violent outbursts",
        ]
    elif "transition" in lowered:
        queries = [
            "preschool Montessori transition difficulty self regulation",
            "toddler early childhood executive function transitions",
        ]
    elif "peer" in lowered:
        queries = [
            "preschool Montessori peer conflict prosocial behavior",
            "toddler early childhood classroom boundary setting",
        ]
    else:
        queries = [
            "preschool Montessori emotional regulation classroom",
            "toddler early childhood work cycle engagement",
        ]
    return {
        "queries": queries,
        "rationale": "Fallback query generation based on dominant classroom patterns.",
    }


def _chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict | None:
    client = _get_client()
    if client is None:
        return None
    response = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_search_queries(student_name: str, patterns: str, summary: str, severity: str) -> dict:
    emergency = _contains_emergency_language(f"{patterns}\n{summary}")
    payload = _chat_json(
        QUERY_PROMPT,
        (
            f"Student: {student_name}\n"
            f"Severity: {severity}\n"
            f"Behavioral patterns: {patterns}\n"
            f"Summary: {summary}"
        ),
        temperature=0.3,
    )
    if payload is None:
        return _fallback_queries(patterns, summary, emergency)
    queries = payload.get("queries") or []
    payload["queries"] = [query.strip() for query in queries if str(query).strip()][:2]
    if len(payload["queries"]) < 2:
        return _fallback_queries(patterns, summary, emergency)
    return payload


def assess_note(student_name: str, note_body: str) -> dict:
    payload = _chat_json(
        SYSTEM_PROMPT,
        f"Student: {student_name}\n\nObservation Note:\n\n{note_body}",
        temperature=0.2,
    )
    if payload is None:
        return _fallback_note_assessment(student_name, note_body)

    payload["student_name"] = student_name
    if payload.get("severity") not in ("green", "yellow", "red"):
        payload["severity"] = "red" if _contains_emergency_language(note_body) else "yellow"
    return payload


def assess_student_history(student_name: str, notes: list[dict]) -> dict:
    if not notes:
        return _fallback_history_assessment(student_name, [])

    history_lines = []
    for note in notes[-12:]:
        history_lines.append(f"Note #{note['id']}: {note['body']}")

    payload = _chat_json(
        HISTORY_PROMPT,
        (
            f"Student: {student_name}\n"
            f"Total notes: {len(notes)}\n\n"
            f"Recent note history:\n\n" + "\n\n".join(history_lines)
        ),
        temperature=0.2,
    )
    if payload is None:
        return _fallback_history_assessment(student_name, notes)

    payload["student_name"] = student_name
    if payload.get("severity") not in ("green", "yellow", "red"):
        payload["severity"] = "red" if _contains_emergency_language("\n".join(note["body"] for note in notes)) else "yellow"

    for key in ("personality_traits", "regulation_triggers", "support_strategies", "knowledge_gaps"):
        value = payload.get(key)
        if isinstance(value, list):
            payload[key] = _dedupe(str(item) for item in value)
        elif isinstance(value, str):
            payload[key] = _split_patterns(value)
        else:
            payload[key] = []

    payload["emergency_action_required"] = bool(
        payload.get("emergency_action_required") or _contains_emergency_language("\n".join(note["body"] for note in notes))
    )
    return payload


def summarize_research_work(student_name: str, query: str, title: str, abstract: str, context: str) -> dict:
    clipped_abstract = abstract[:3000]
    payload = _chat_json(
        RESEARCH_SUMMARY_PROMPT,
        (
            f"Student: {student_name}\n"
            f"Research query: {query}\n"
            f"Student context: {context}\n"
            f"Paper title: {title}\n"
            f"Paper abstract: {clipped_abstract}"
        ),
        temperature=0.2,
    )
    if payload is not None:
        insights = payload.get("insights") or []
        related_topics = payload.get("related_topics") or []
        return {
            "insights": _dedupe(str(item) for item in insights)[:2],
            "related_topics": _dedupe(str(item) for item in related_topics)[:2],
            "confidence": float(payload.get("confidence") or 0.72),
        }

    sentences = re.split(r"(?<=[.!?])\s+", clipped_abstract.strip()) if clipped_abstract else []
    insights = [sentence.strip() for sentence in sentences if sentence.strip()][:2]
    if not insights:
        insights = [f"{title} was retrieved for query '{query}' and should be reviewed for classroom relevance."]
    related_topics = _dedupe(_split_patterns(context) + _split_patterns(query))[:2]
    return {
        "insights": insights[:2],
        "related_topics": related_topics or ["early childhood classroom regulation"],
        "confidence": 0.68,
    }
