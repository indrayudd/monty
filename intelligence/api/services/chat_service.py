"""Ask Monty chat service — context-aware conversational query over the wiki."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from openai import OpenAI

from intelligence.api.services.ghost_client import _conn
from intelligence.api.services.wiki_paths import WIKI_ROOT


STUDENT_NAMES = ["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]

SYSTEM_PROMPT = """You are Ask Monty, an informative assistant embedded in a Montessori early-childhood behavioral knowledge wiki. You answer questions using the wiki's behavioral knowledge graph and student observation data.

CRITICAL RULES:
1. For GENERAL behavioral questions (e.g., "What triggers emotional outbursts?", "How does self-regulation develop?"), answer ONLY from the anonymized behavioral knowledge graph. Do NOT mention any student by name. Use phrases like "children in the classroom", "a child", "some children".
2. For STUDENT-SPECIFIC questions (e.g., "How is Mira doing?", "Tell me about Arjun's patterns"), you MAY reference that specific student's data.
3. Never volunteer student names unprompted. If the user asks a general question, keep it general.
4. Cite wiki page paths in brackets like [behavioral/antecedents/peer-disruption] when referencing specific knowledge.
5. Be informative, direct, calm, and technically credible. Not overly conversational.
6. If you can't answer from the available context, say so clearly and suggest what wiki pages might help.

You have access to the following context from the wiki:"""


def _openai_client() -> OpenAI | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    return OpenAI(api_key=key)


def _detect_student_query(question: str) -> str | None:
    """Return the student name if the question asks about a specific student."""
    q_lower = question.lower()
    for name in STUDENT_NAMES:
        if name.lower() in q_lower or name.split()[0].lower() in q_lower:
            return name
    return None


def _gather_context(
    question: str,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> str:
    """Build context string from wiki content + behavioral KG."""
    parts: list[str] = []

    # 1. Current page content (if provided)
    if current_page_path:
        full_path = WIKI_ROOT / current_page_path
        if full_path.exists() and full_path.is_file():
            content = full_path.read_text(encoding="utf-8")[:3000]
            parts.append(f"## Currently viewing: {current_page_path}\n{content}")

    # 2. Selected text
    if selected_text:
        parts.append(f"## User's selected text:\n{selected_text[:500]}")

    # 3. Check if student-specific
    student = _detect_student_query(question)

    if student:
        # Load student profile + recent incidents
        student_dir = WIKI_ROOT / "students" / student.replace(" ", "_")
        profile = student_dir / "profile.md"
        if profile.exists():
            parts.append(f"## Student profile: {student}\n{profile.read_text(encoding='utf-8')[:2000]}")
        patterns = student_dir / "patterns.md"
        if patterns.exists():
            parts.append(f"## Student patterns: {student}\n{patterns.read_text(encoding='utf-8')[:1500]}")
        # Recent incidents
        incidents_dir = student_dir / "incidents"
        if incidents_dir.exists():
            incident_files = sorted(incidents_dir.glob("*.md"))[-5:]  # last 5
            for f in incident_files:
                parts.append(f"## Incident: {f.name}\n{f.read_text(encoding='utf-8')[:800]}")
    else:
        # General query — use anonymized behavioral KG only
        parts.append("## Behavioral Knowledge Graph (anonymized, no student names)")
        conn = _conn()
        try:
            cur = conn.cursor()
            # Find relevant behavioral nodes by keyword matching
            keywords = [w for w in question.lower().split() if len(w) > 3]
            if keywords:
                like_clauses = " OR ".join(["title LIKE ? OR summary LIKE ?"] * len(keywords))
                params = []
                for kw in keywords:
                    params.extend([f"%{kw}%", f"%{kw}%"])
                cur.execute(
                    f"SELECT slug, type, title, summary, support_count, students_count "
                    f"FROM behavioral_nodes WHERE {like_clauses} "
                    f"ORDER BY support_count DESC LIMIT 15",
                    params,
                )
                rows = cur.fetchall()
                if rows:
                    for r in rows:
                        parts.append(
                            f"- [{r[1]}] {r[2]} (slug: {r[0]}, "
                            f"support: {r[4]}, students: {r[5]})"
                            f"{': ' + r[3] if r[3] else ''}"
                        )

            # Also include the wiki index for navigation help
            index_path = WIKI_ROOT / "index.md"
            if index_path.exists():
                parts.append(f"## Wiki index (for navigation)\n{index_path.read_text(encoding='utf-8')[:2000]}")
        finally:
            conn.close()

    return "\n\n".join(parts)


def stream_chat(
    question: str,
    history: list[dict] | None = None,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> Generator[str, None, None]:
    """Stream a chat response. Yields text chunks."""
    client = _openai_client()
    if client is None:
        yield "Ask Monty requires an OpenAI API key. Set OPENAI_API_KEY in your environment."
        return

    context = _gather_context(question, current_page_path, selected_text)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
    ]

    # Add conversation history (last 10 turns)
    if history:
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": question})

    try:
        stream = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=800,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n\n_Error: {e}_"
