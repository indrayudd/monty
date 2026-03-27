from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from intelligence.api.services.ghost_client import (
    get_knowledge_graph_entries,
    insert_literature,
    upsert_knowledge_graph_entry,
)
from intelligence.api.services.llm_service import (
    generate_search_queries,
    summarize_research_work,
)
from notes_streamer.literature_scraping.api_usage_example import (
    OpenAlexClient,
    extract_abstract_text,
    extract_basic_metadata,
    score_work_for_selection,
)


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


OPENALEX_FILTER = "open_access.is_oa:true,topics.id:T10589|T13987|T14290,publication_year:>2009"
OPENALEX_SELECT = (
    "id,display_name,publication_year,cited_by_count,abstract_inverted_index,authorships,"
    "primary_location,best_oa_location,open_access,has_content,ids"
)
OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def _openalex_client() -> OpenAlexClient | None:
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAlexClient(api_key=api_key, user_agent="monty-agentic-loop/0.2")


def _normalize_context(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    parts: list[str] = []
    for key, value in context.items():
        if isinstance(value, list):
            joined = ", ".join(str(item) for item in value if str(item).strip())
            if joined:
                parts.append(f"{key}: {joined}")
        elif value not in (None, ""):
            parts.append(f"{key}: {value}")
    return " | ".join(parts)


def _related_topics_from_context(query: str, context: dict[str, Any] | None) -> list[str]:
    related: list[str] = [query]
    if not context:
        return related
    for value in context.values():
        if isinstance(value, list):
            related.extend(str(item) for item in value if str(item).strip())
        elif value not in (None, ""):
            related.append(str(value))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in related:
        cleaned = item.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped[:4]


def _store_openalex_result(student_name: str | None, query: str, work: dict, context_text: str) -> dict | None:
    meta = extract_basic_metadata(work)
    openalex_id = meta.get("openalex_id") or ""
    if not openalex_id:
        return None

    abstract = extract_abstract_text(work)
    title = meta.get("title") or "Untitled"
    authors_str = ", ".join(meta.get("authors", []))
    summary = summarize_research_work(
        student_name=student_name or "Shared KG",
        query=query,
        title=title,
        abstract=abstract,
        context=context_text,
    )

    if student_name:
        insert_literature(
            {
                "student_name": student_name,
                "search_query": query,
                "openalex_id": openalex_id,
                "title": title,
                "authors": authors_str,
                "publication_year": meta.get("publication_year"),
                "cited_by_count": meta.get("cited_by_count", 0),
                "abstract": abstract[:2000] if abstract else None,
                "landing_page_url": meta.get("landing_page_url"),
                "relevance_summary": context_text[:500] if context_text else f"Matched query: {query}",
            }
        )

    entry = {
        "student_name": student_name,
        "topic": query,
        "search_query": query,
        "source_title": title,
        "source_url": meta.get("landing_page_url") or f"https://openalex.org/{openalex_id}",
        "insights": summary.get("insights") or [],
        "related_topics": summary.get("related_topics") or _related_topics_from_context(query, {"context": context_text}),
        "confidence": summary.get("confidence") or 0.7,
        "evidence_summary": context_text or abstract[:500],
    }
    upsert_knowledge_graph_entry(entry)
    return entry


def enrich_student_knowledge(
    student_name: str,
    assessment: dict,
    emergency_terms: list[str] | None = None,
    verbose: bool = False,
) -> dict:
    existing = get_knowledge_graph_entries(student_name=student_name, query=assessment.get("behavioral_patterns"), limit=6)
    if existing and len(existing) >= 2 and not emergency_terms:
        if verbose:
            print(
                f"[kg-agent] {student_name}: reusing {len(existing)} existing KG node(s) "
                "for current profile context",
                flush=True,
            )
        return {"results": existing, "new_nodes_created": 0, "queries": []}

    client = _openalex_client()
    if client is None:
        if verbose:
            print(f"[kg-agent] {student_name}: OPENALEX_API_KEY not set, skipping remote enrichment", flush=True)
        return {"results": existing, "new_nodes_created": 0, "queries": []}

    queries_payload = generate_search_queries(
        student_name=student_name,
        patterns=assessment.get("behavioral_patterns", ""),
        summary=assessment.get("profile_summary", ""),
        severity=assessment.get("severity", "yellow"),
    )
    queries = list(queries_payload.get("queries") or [])

    if emergency_terms:
        queries.insert(0, "preschool Montessori aggression de escalation classroom")
        queries.insert(1, "toddler early childhood self harm violent dysregulation")

    seen_queries: set[str] = set()
    ordered_queries: list[str] = []
    for query in queries:
        cleaned = query.strip()
        if not cleaned or cleaned.lower() in seen_queries:
            continue
        seen_queries.add(cleaned.lower())
        ordered_queries.append(cleaned)

    if verbose:
        print(
            f"[kg-agent] {student_name}: existing_nodes={len(existing)} "
            f"emergency={bool(emergency_terms)} queries={ordered_queries[:3]}",
            flush=True,
        )

    context_text = " | ".join(
        part
        for part in [
            assessment.get("profile_summary", ""),
            assessment.get("behavioral_patterns", ""),
            ", ".join(assessment.get("knowledge_gaps", []) or []),
            ", ".join(emergency_terms or []),
        ]
        if part
    )

    new_nodes = 0
    for query in ordered_queries[:3]:
        if verbose:
            request_url = client.build_url(
                OPENALEX_WORKS_URL,
                params={
                    "search": query,
                    "per_page": 10,
                    "filter": OPENALEX_FILTER,
                    "select": OPENALEX_SELECT,
                },
            )
            print(f"[kg-agent] {student_name}: OpenAlex search -> {query}", flush=True)
            print(f"[kg-agent][http] GET {request_url}", flush=True)
        search_resp = client.search_works(
            topic_query=query,
            per_page=10,
            extra_filter=OPENALEX_FILTER,
            select=OPENALEX_SELECT,
        )
        candidates = search_resp.get("results", [])
        if verbose:
            print(
                f"[kg-agent] {student_name}: OpenAlex returned {len(candidates)} candidate(s) for '{query}'",
                flush=True,
            )
        ranked = sorted(candidates, key=score_work_for_selection, reverse=True)
        for work in ranked[:2]:
            stored = _store_openalex_result(student_name, query, work, context_text)
            if stored:
                new_nodes += 1
                if verbose:
                    print(
                        f"[kg-agent] {student_name}: stored KG node '{stored['source_title']}' "
                        f"topics={stored['related_topics']}",
                        flush=True,
                    )
                    print(
                        f"[kg-agent][paper] {student_name}: source_url={stored['source_url']}",
                        flush=True,
                    )

    results = get_knowledge_graph_entries(student_name=student_name, query=assessment.get("behavioral_patterns"), limit=8)
    if verbose:
        print(
            f"[kg-agent] {student_name}: knowledge refresh complete total_nodes={len(results)} new_nodes={new_nodes}",
            flush=True,
        )
    return {"results": results, "new_nodes_created": new_nodes, "queries": ordered_queries[:3]}


def query_knowledge_graph(query: str, context: dict[str, Any] | None = None) -> dict:
    context_text = _normalize_context(context)
    student_name = None
    if context and context.get("student_name"):
        student_name = str(context["student_name"])

    existing = get_knowledge_graph_entries(student_name=student_name, query=query, limit=8)
    if len(existing) >= 3:
        return {"results": existing, "new_nodes_created": 0}

    client = _openalex_client()
    if client is None:
        return {"results": existing, "new_nodes_created": 0}

    search_terms = query
    if context_text:
        search_terms = f"{query} {context_text}"

    search_resp = client.search_works(
        topic_query=search_terms,
        per_page=8,
        extra_filter=OPENALEX_FILTER,
        select=OPENALEX_SELECT,
    )
    candidates = search_resp.get("results", [])
    ranked = sorted(candidates, key=score_work_for_selection, reverse=True)

    new_nodes = 0
    for work in ranked[:3]:
        stored = _store_openalex_result(student_name, query, work, context_text or json.dumps(context or {}))
        if stored:
            new_nodes += 1

    results = get_knowledge_graph_entries(student_name=student_name, query=query, limit=8)
    return {"results": results, "new_nodes_created": new_nodes}
