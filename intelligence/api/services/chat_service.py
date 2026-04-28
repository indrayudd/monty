"""Ask Monty chat service — context-aware conversational query over the wiki."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from openai import OpenAI

from intelligence.api.services.ghost_client import _conn
from intelligence.api.services.wiki_paths import WIKI_ROOT
import frontmatter


STUDENT_NAMES = ["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]

SYSTEM_PROMPT = """You are Ask Monty, an informative assistant embedded in a Montessori early-childhood behavioral knowledge wiki. You answer questions using the wiki's behavioral knowledge graph and student observation data.

CRITICAL RULES:
1. For GENERAL behavioral questions (e.g., "What triggers emotional outbursts?", "How does self-regulation develop?"), answer ONLY from the anonymized behavioral knowledge graph. Do NOT mention any student by name. Use phrases like "children in the classroom", "a child", "some children".
2. For STUDENT-SPECIFIC questions (e.g., "How is Mira doing?", "Tell me about Arjun's patterns"), you MAY reference that specific student's data.
3. Never volunteer student names unprompted. If the user asks a general question, keep it general.
4. CITE your sources using numbered superscripts like [1], [2], [3] that correspond to the numbered source list provided below. Every factual claim should have at least one citation. Place the citation immediately after the claim.
5. Be informative, direct, calm, and technically credible. Not overly conversational.
6. If you can't answer from the available context, say so clearly and suggest what wiki pages might help.
7. Do NOT include a sources/references section at the end. The UI renders source attributions automatically from the source numbers.

You have access to the following numbered sources from the wiki:"""

PAGE_SELECT_PROMPT = """You are a retrieval assistant for a Montessori behavioral knowledge wiki.
Given the wiki index below and the user's question, return a JSON array of file paths to read.
Select 5-15 pages most likely to contain or contribute to the answer.

Prefer:
- Behavioral nodes with high support counts relevant to the question
- Research papers whose titles relate to the topic
- Student profiles/incidents if the question names a specific child
- Edge files that connect relevant behavioral patterns

Return ONLY a JSON array of path strings, nothing else.
Example: ["behavioral/behaviors/shutdown-stillness-avoidance.md", "sources/openalex/W1556609206.md"]"""


def _load_index() -> str:
    """Read wiki/index.md in full."""
    index_path = WIKI_ROOT / "index.md"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return ""


def _select_pages(question: str, index_text: str) -> list[str]:
    """Ask LLM to select relevant wiki pages from the index."""
    import json

    client = _openai_client()
    if client is None:
        return []

    try:
        resp = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=[
                {"role": "system", "content": PAGE_SELECT_PROMPT + "\n\n" + index_text},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_completion_tokens=400,
        )
        content = resp.choices[0].message.content or "[]"
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        paths = json.loads(content)
        if isinstance(paths, list):
            return [p for p in paths if isinstance(p, str)]
    except Exception:
        pass
    return []


import re as _re


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    return len(text) // 4


def _extract_link_candidates(content: str, meta: dict) -> list[str]:
    """Extract outgoing wiki paths from page content and frontmatter."""
    candidates: list[str] = []

    # behavioral_refs from incident frontmatter
    for ref in meta.get("behavioral_refs", []) or []:
        candidates.append(ref + ".md")

    # src_slug / dst_slug from edge frontmatter
    for key in ("src_slug", "dst_slug"):
        val = meta.get(key)
        if val:
            candidates.append("behavioral/" + val + ".md" if not val.startswith("behavioral/") else val + ".md")

    # related_nodes from node frontmatter
    for ref in meta.get("related_nodes", []) or []:
        if not ref.endswith(".md"):
            ref += ".md"
        candidates.append(ref)

    # fetched_for_student -> student profile
    student = meta.get("fetched_for_student")
    if student:
        candidates.append(f"students/{student.replace(' ', '_')}/profile.md")

    # Markdown links [text](relative-path) - skip external URLs
    for m in _re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', content):
        href = m.group(2)
        if not href.startswith("http") and not href.startswith("#") and not href.startswith("mailto"):
            candidates.append(href)

    # Wiki-style [[slug]] links
    for m in _re.finditer(r'\[\[([^\]]+)\]\]', content):
        candidates.append(m.group(1))

    return candidates


def _read_page(path_str: str) -> tuple[str, dict, str]:
    """Read a wiki page, return (path_str, frontmatter_dict, full_text)."""
    full_path = WIKI_ROOT / path_str
    if not full_path.exists() or not full_path.is_file():
        return (path_str, {}, "")
    try:
        post = frontmatter.load(full_path)
        return (path_str, dict(post.metadata), post.content)
    except Exception:
        text = full_path.read_text(encoding="utf-8")
        return (path_str, {}, text)


def _fallback_keyword_select(question: str) -> list[str]:
    """Fallback when LLM page selection fails: keyword match against DB."""
    conn = _conn()
    try:
        cur = conn.cursor()
        keywords = [w for w in question.lower().split() if len(w) > 3]
        paths: list[str] = []
        if keywords:
            like_clauses = " OR ".join(["title LIKE ? OR summary LIKE ?"] * len(keywords))
            params = []
            for kw in keywords:
                params.extend([f"%{kw}%", f"%{kw}%"])
            cur.execute(
                f"SELECT slug, type FROM behavioral_nodes WHERE {like_clauses} "
                f"ORDER BY support_count DESC LIMIT 10",
                params,
            )
            for row in cur.fetchall():
                slug, ntype = row[0], row[1]
                for btype in ("setting_events", "antecedents", "behaviors",
                              "functions", "brain_states", "responses", "protective_factors"):
                    if ntype in btype or btype.startswith(ntype):
                        paths.append(f"behavioral/{btype}/{slug}.md")
                        break
        student = _detect_student_query(question)
        if student:
            sdir = f"students/{student.replace(' ', '_')}"
            paths.append(f"{sdir}/profile.md")
            paths.append(f"{sdir}/patterns.md")
        return paths
    finally:
        conn.close()


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
) -> tuple[str, list[str]]:
    """Build context via index-guided adaptive graph traversal.

    Returns (context_string, source_paths) where source_paths is an ordered
    list of wiki paths corresponding to [1], [2], ... citations.
    """
    parts: list[str] = []
    read_paths: set[str] = set()
    source_paths: list[str] = []  # ordered, [1]-indexed for citations
    token_count = 0

    def _add_source(path_str: str, content: str, label: str = "Source") -> None:
        nonlocal token_count
        source_paths.append(path_str)
        idx = len(source_paths)
        page_tokens = _estimate_tokens(content)
        parts.append(f"## [{idx}] {label}: {path_str}\n{content}")
        token_count += page_tokens

    # 1. Current page context (if user is viewing one)
    if current_page_path:
        full_path = WIKI_ROOT / current_page_path
        if full_path.exists() and full_path.is_file():
            content = full_path.read_text(encoding="utf-8")[:3000]
            _add_source(current_page_path, content, "Currently viewing")
            read_paths.add(current_page_path)

    # 2. Selected text
    if selected_text:
        snippet = selected_text[:500]
        parts.append(f"## User's selected text:\n{snippet}")
        token_count += _estimate_tokens(snippet)

    # 3. LLM-guided page selection from index
    index_text = _load_index()
    selected = _select_pages(question, index_text)

    # Fallback: if page selection returned nothing, try keyword matching
    if not selected:
        selected = _fallback_keyword_select(question)

    # 4. Read selected pages (budget: ~8K tokens)
    SELECT_BUDGET = 8000
    select_tokens_used = 0
    all_link_candidates: list[str] = []

    for path_str in selected:
        if path_str in read_paths:
            continue
        if select_tokens_used >= SELECT_BUDGET:
            break
        path_str_clean = path_str.lstrip("/")
        _, meta, content = _read_page(path_str_clean)
        if not content:
            continue
        page_text = content[:2000]
        _add_source(path_str_clean, page_text)
        select_tokens_used += _estimate_tokens(page_text)
        read_paths.add(path_str_clean)

        all_link_candidates.extend(_extract_link_candidates(content, meta))

    # 5. Adaptive expansion
    if select_tokens_used < 4000:
        expansion_budget = 8000
        allow_2hop = True
    elif select_tokens_used < 8000:
        expansion_budget = 4000
        allow_2hop = False
    else:
        expansion_budget = 2000
        allow_2hop = False

    from collections import Counter
    candidate_counts = Counter(all_link_candidates)
    for rp in read_paths:
        candidate_counts.pop(rp, None)

    expansion_tokens_used = 0
    hop2_candidates: list[str] = []

    for candidate_path, _count in candidate_counts.most_common():
        if expansion_tokens_used >= expansion_budget:
            break
        candidate_clean = candidate_path.lstrip("/")
        if candidate_clean in read_paths:
            continue
        _, meta, content = _read_page(candidate_clean)
        if not content:
            continue
        page_text = content[:1500]
        _add_source(candidate_clean, page_text, "Linked")
        expansion_tokens_used += _estimate_tokens(page_text)
        read_paths.add(candidate_clean)

        if allow_2hop:
            hop2_candidates.extend(_extract_link_candidates(content, meta))

    # 2-hop expansion
    if allow_2hop and hop2_candidates:
        hop2_counts = Counter(hop2_candidates)
        for rp in read_paths:
            hop2_counts.pop(rp, None)
        remaining = expansion_budget - expansion_tokens_used
        for candidate_path, _count in hop2_counts.most_common():
            if remaining <= 0:
                break
            candidate_clean = candidate_path.lstrip("/")
            if candidate_clean in read_paths:
                continue
            _, meta, content = _read_page(candidate_clean)
            if not content:
                continue
            page_text = content[:1000]
            _add_source(candidate_clean, page_text, "Linked (2-hop)")
            remaining -= _estimate_tokens(page_text)
            read_paths.add(candidate_clean)

    return "\n\n".join(parts), source_paths


def get_sources(
    question: str,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> list[str]:
    """Return the source paths that would be used for a query (for the API to send alongside the stream)."""
    _, source_paths = _gather_context(question, current_page_path, selected_text)
    return source_paths


def stream_chat(
    question: str,
    history: list[dict] | None = None,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> Generator[str, None, None]:
    """Stream a chat response. Yields text chunks.

    The first yielded chunk is a JSON line with source paths:
    {"sources": ["path1.md", "path2.md", ...]}
    Followed by the actual response text chunks.
    """
    import json as _json

    client = _openai_client()
    if client is None:
        yield _json.dumps({"sources": []}) + "\n"
        yield "Ask Monty requires an OpenAI API key. Set OPENAI_API_KEY in your environment."
        return

    context, source_paths = _gather_context(question, current_page_path, selected_text)

    # Emit sources as the first line so the frontend can render attribution
    yield _json.dumps({"sources": source_paths}) + "\n"

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
