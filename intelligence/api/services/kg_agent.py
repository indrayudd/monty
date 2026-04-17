from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import frontmatter as _fm

from intelligence.api.services.curiosity import evaluate_gate
from intelligence.api.services.ghost_client import (
    _conn,
    _fetchall,
)
from intelligence.api.services.llm_service import (
    generate_search_queries,
    summarize_research_work,
)
from intelligence.api.services.wiki_paths import source_paper_path, student_dir
from notes_streamer.literature_scraping.api_usage_example import (
    OpenAlexClient,
    extract_abstract_text,
    extract_basic_metadata,
    score_work_for_selection,
)

_log = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Wiki paper-page helpers (Task 3.3)
# ---------------------------------------------------------------------------

def _write_paper_page(meta: dict, abstract: str, summary: dict, query: str, student_name: str | None) -> str:
    """Write a markdown page for an OpenAlex paper under wiki/sources/openalex/."""
    path = source_paper_path(meta.get("openalex_id", "unknown"))
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_meta = {
        "openalex_id": meta.get("openalex_id"),
        "title": meta.get("title"),
        "authors": meta.get("authors", []),
        "publication_year": meta.get("publication_year"),
        "cited_by_count": meta.get("cited_by_count", 0),
        "landing_page_url": meta.get("landing_page_url"),
        "fetched_for_query": query,
        "fetched_for_student": student_name,
    }
    body = (
        f"# {meta.get('title')}\n\n"
        f"## Relevance\n\n{summary.get('relevance', '')}\n\n"
        f"## Abstract\n\n{(abstract or '')[:2000]}\n\n"
        f"## Insights\n\n"
        + "\n".join(f"- {i}" for i in (summary.get("insights") or []))
        + "\n"
    )
    post = _fm.Post(content=body, **fm_meta)
    path.write_text(_fm.dumps(post) + "\n", encoding="utf-8")
    return str(path)


def _link_paper_to_student(student_name: str, paper_meta: dict) -> None:
    """Append a paper link to the student's wiki/students/<name>/literature.md."""
    sdir = student_dir(student_name)
    sdir.mkdir(parents=True, exist_ok=True)
    lit = sdir / "literature.md"
    openalex_id = paper_meta.get("openalex_id", "")
    safe_id = openalex_id.split("/")[-1]
    title = paper_meta.get("title", "Untitled")
    year = paper_meta.get("publication_year", "")
    line = f"- [{title}](../../sources/openalex/{safe_id}.md) — {year}\n"
    if not lit.exists():
        lit.write_text(f"# {student_name} — Research Literature\n\n", encoding="utf-8")
    with lit.open("a", encoding="utf-8") as f:
        f.write(line)


def _wiki_paper_entries(student_name: str | None, query: str | None, limit: int = 8) -> list[dict]:
    """Return paper entries from the wiki index (behavioral_nodes / student_incidents)
    as a list of lightweight dicts — replaces the legacy get_knowledge_graph_entries call."""
    try:
        conn = _conn()
        try:
            cur = conn.cursor()
            if student_name:
                cur.execute(
                    "SELECT slug, summary, literature_refs, last_research_fetched_at "
                    "FROM behavioral_nodes WHERE summary LIKE ? LIMIT ?",
                    (f"%{(query or '')[:60]}%", limit),
                )
            else:
                cur.execute(
                    "SELECT slug, summary, literature_refs, last_research_fetched_at "
                    "FROM behavioral_nodes LIMIT ?",
                    (limit,),
                )
            rows = _fetchall(cur)
        finally:
            conn.close()
        return rows
    except Exception:
        return []


def _mark_node_researched(slug_full: str, paper_count: int) -> None:
    """Update behavioral_nodes.last_research_fetched_at and increment literature_refs."""
    slug = slug_full.split("/")[-1]
    try:
        conn = _conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE behavioral_nodes SET last_research_fetched_at = CURRENT_TIMESTAMP, "
                "literature_refs = literature_refs + ? WHERE slug = ?",
                (paper_count, slug),
            )
            cur.execute(
                "UPDATE curiosity_events SET paper_count = ? "
                "WHERE node_slug = ? AND fired_at = ("
                "  SELECT MAX(fired_at) FROM curiosity_events WHERE node_slug = ?"
                ")",
                (paper_count, slug_full, slug_full),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        _log.warning("_mark_node_researched failed for %s: %s", slug_full, exc)


def _curious_nodes_for_assessment(assessment: dict) -> list[str]:
    """Return slugs of behavioral nodes whose curiosity gate fires."""
    nodes = assessment.get("behavioral_nodes") or []
    fired: list[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        slug_full = f"{n.get('type', 'behaviors')}/{n.get('slug', '')}"
        try:
            result = evaluate_gate(slug_full)
            if result.get("fire"):
                fired.append(slug_full)
        except Exception as exc:
            _log.debug("evaluate_gate(%s) failed: %s", slug_full, exc)
    return fired


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

    # Write a wiki markdown page for the paper
    try:
        _write_paper_page(meta, abstract, summary, query, student_name)
        if student_name:
            _link_paper_to_student(student_name, meta)
    except Exception as exc:
        _log.warning("wiki paper-page write failed for %s: %s", openalex_id, exc)

    return entry


def enrich_student_knowledge(
    student_name: str,
    assessment: dict,
    emergency_terms: list[str] | None = None,
    verbose: bool = False,
) -> dict:
    existing = _wiki_paper_entries(student_name=student_name, query=assessment.get("behavioral_patterns"), limit=6)

    # Phase 3: third trigger — curiosity gate fires for any behavioral node in the assessment
    curious_nodes: list[str] = _curious_nodes_for_assessment(assessment)

    if existing and len(existing) >= 2 and not emergency_terms and not curious_nodes:
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

    # Phase 3: prepend curious node slugs as additional seed terms
    if curious_nodes:
        if verbose:
            print(
                f"[kg-agent] {student_name}: curiosity gate fired for nodes={curious_nodes}",
                flush=True,
            )
        for slug_full in reversed(curious_nodes):
            seed_term = slug_full.replace("/", " ").replace("-", " ")
            queries.insert(0, f"montessori early childhood {seed_term}")

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

    # Phase 3: mark curious nodes as researched (updates last_research_fetched_at + literature_refs)
    if curious_nodes and new_nodes > 0:
        per_node = max(1, new_nodes // len(curious_nodes))
        for slug_full in curious_nodes:
            _mark_node_researched(slug_full, per_node)

    results = _wiki_paper_entries(student_name=student_name, query=assessment.get("behavioral_patterns"), limit=8)
    if verbose:
        print(
            f"[kg-agent] {student_name}: knowledge refresh complete total_nodes={len(results)} new_nodes={new_nodes}",
            flush=True,
        )
    return {
        "results": results,
        "new_nodes_created": new_nodes,
        "queries": ordered_queries[:3],
        "curious_nodes": curious_nodes,
    }


def _pluralize_type(node_type: str) -> str:
    """Convert singular node type to plural for edge slug prefix."""
    if node_type.endswith("s"):
        return node_type
    return node_type + "s"


def discover_research_edges(verbose: bool = False, max_pairs: int = 3) -> dict:
    """Proactively discover research-backed edges between well-supported but
    disconnected behavioral nodes. Called during idle cycles."""
    result = {"pairs_checked": 0, "edges_created": 0, "papers_fetched": 0}

    client = _openalex_client()
    if client is None:
        if verbose:
            print("[research-edges] OPENALEX_API_KEY not set, skipping", flush=True)
        return result

    # Ensure the research_edge_checks table exists
    from intelligence.api.services.ghost_client import ensure_agent_tables
    ensure_agent_tables()

    conn = _conn()
    try:
        cur = conn.cursor()
        # Find candidate pairs: well-supported nodes of different types with no
        # existing edge and not recently checked.
        # behavioral_edges stores type-prefixed slugs (e.g. "antecedents/peer-disruption")
        # while behavioral_nodes stores bare slugs (e.g. "peer-disruption") with a
        # separate type column (singular, e.g. "antecedent").
        cur.execute(
            """
            SELECT
                a.slug AS slug_a, a.type AS type_a, a.title AS title_a, a.support_count AS sc_a,
                b.slug AS slug_b, b.type AS type_b, b.title AS title_b, b.support_count AS sc_b
            FROM behavioral_nodes a
            JOIN behavioral_nodes b ON a.slug < b.slug AND a.type != b.type
            WHERE a.support_count >= 5 AND b.support_count >= 5
              -- No existing edge in either direction (account for plural prefix)
              AND NOT EXISTS (
                SELECT 1 FROM behavioral_edges e
                WHERE (
                  (e.src_slug = (CASE WHEN a.type LIKE '%s' THEN a.type ELSE a.type || 's' END) || '/' || a.slug
                   AND e.dst_slug = (CASE WHEN b.type LIKE '%s' THEN b.type ELSE b.type || 's' END) || '/' || b.slug)
                  OR
                  (e.src_slug = (CASE WHEN b.type LIKE '%s' THEN b.type ELSE b.type || 's' END) || '/' || b.slug
                   AND e.dst_slug = (CASE WHEN a.type LIKE '%s' THEN a.type ELSE a.type || 's' END) || '/' || a.slug)
                )
              )
              -- Not checked within the last 24 hours
              AND NOT EXISTS (
                SELECT 1 FROM research_edge_checks rc
                WHERE rc.slug_a = a.slug AND rc.slug_b = b.slug
                  AND rc.checked_at > datetime('now', '-24 hours')
              )
              AND NOT EXISTS (
                SELECT 1 FROM research_edge_checks rc
                WHERE rc.slug_a = b.slug AND rc.slug_b = a.slug
                  AND rc.checked_at > datetime('now', '-24 hours')
              )
            ORDER BY (a.support_count + b.support_count) DESC
            LIMIT ?
            """,
            (max_pairs,),
        )
        pairs = _fetchall(cur)
    finally:
        conn.close()

    if verbose:
        print(f"[research-edges] found {len(pairs)} candidate pair(s) to investigate", flush=True)

    for pair in pairs:
        slug_a = pair["slug_a"]
        slug_b = pair["slug_b"]
        type_a = pair["type_a"]
        type_b = pair["type_b"]
        title_a = pair["title_a"]
        title_b = pair["title_b"]

        query_str = f"toddler preschool Montessori {title_a} {title_b} relationship"
        if verbose:
            print(f"[research-edges] searching: {query_str}", flush=True)

        try:
            search_resp = client.search_works(
                topic_query=query_str,
                per_page=3,
                extra_filter=OPENALEX_FILTER,
                select=OPENALEX_SELECT,
            )
        except Exception as exc:
            _log.warning("OpenAlex search failed for pair %s/%s: %s", slug_a, slug_b, exc)
            # Record the check so we don't retry immediately
            _record_edge_check(slug_a, slug_b, found=False)
            result["pairs_checked"] += 1
            continue

        candidates = search_resp.get("results", [])
        if verbose:
            print(f"[research-edges] OpenAlex returned {len(candidates)} result(s)", flush=True)

        found_connection = False
        for work in candidates[:3]:
            meta = extract_basic_metadata(work)
            openalex_id = meta.get("openalex_id", "")
            if not openalex_id:
                continue

            abstract = extract_abstract_text(work)
            title = meta.get("title") or "Untitled"
            context_text = f"{title_a} and {title_b} relationship in early childhood"

            summary = summarize_research_work(
                student_name="Shared KG",
                query=query_str,
                title=title,
                abstract=abstract,
                context=context_text,
            )
            result["papers_fetched"] += 1

            # Check if the summary mentions both concepts and suggests a relationship
            relevance = summary.get("relevance", "")
            insights = summary.get("insights", [])
            combined_text = f"{relevance} {' '.join(str(i) for i in insights)}".lower()
            mentions_a = title_a.lower().split()[0] in combined_text if title_a else False
            mentions_b = title_b.lower().split()[0] in combined_text if title_b else False

            if mentions_a and mentions_b:
                found_connection = True
                if verbose:
                    print(
                        f"[research-edges] connection found: {slug_a} <-> {slug_b} via '{title}'",
                        flush=True,
                    )

                # Create the research edge via wiki_writer
                from intelligence.api.services.wiki_writer import upsert_behavioral_edge
                evidence = f"[RESEARCH] {title} (OpenAlex {openalex_id}): {'; '.join(str(i) for i in insights[:2])}"
                edge_result = upsert_behavioral_edge(
                    src_type=_pluralize_type(type_a),
                    src_slug=slug_a,
                    rel="research_links",
                    dst_type=_pluralize_type(type_b),
                    dst_slug=slug_b,
                    new_evidence=evidence,
                    new_student_name=None,
                )

                # Add source: research to the edge frontmatter
                try:
                    from intelligence.api.services.wiki_paths import behavioral_edge_path
                    edge_path = behavioral_edge_path(
                        _pluralize_type(type_a), slug_a,
                        "research_links",
                        _pluralize_type(type_b), slug_b,
                    )
                    if edge_path.exists():
                        post = _fm.load(edge_path)
                        post.metadata["source"] = "research"
                        edge_path.write_text(
                            _fm.dumps(post) + ("\n" if not _fm.dumps(post).endswith("\n") else ""),
                            encoding="utf-8",
                        )
                        # Re-index with source field
                        from intelligence.api.services.wiki_indexer import index_behavioral_edge
                        index_behavioral_edge(edge_path)
                except Exception as exc:
                    _log.warning("Failed to add source:research to edge frontmatter: %s", exc)

                # Write paper page
                try:
                    _write_paper_page(meta, abstract, summary, query_str, None)
                except Exception as exc:
                    _log.warning("Failed to write paper page: %s", exc)

                result["edges_created"] += 1
                break  # One connection per pair is enough

        _record_edge_check(slug_a, slug_b, found=found_connection)
        result["pairs_checked"] += 1

    if verbose:
        print(f"[research-edges] done: {result}", flush=True)
    return result


def _record_edge_check(slug_a: str, slug_b: str, found: bool) -> None:
    """Record that a pair was checked in the cooldown table."""
    # Normalize order so (a,b) and (b,a) map to the same row
    if slug_a > slug_b:
        slug_a, slug_b = slug_b, slug_a
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO research_edge_checks (slug_a, slug_b, found_connection)
            VALUES (?, ?, ?)
            ON CONFLICT (slug_a, slug_b) DO UPDATE SET
                checked_at = CURRENT_TIMESTAMP,
                found_connection = EXCLUDED.found_connection
            """,
            (slug_a, slug_b, found),
        )
        conn.commit()
    finally:
        conn.close()


def query_knowledge_graph(query: str, context: dict[str, Any] | None = None) -> dict:
    context_text = _normalize_context(context)
    student_name = None
    if context and context.get("student_name"):
        student_name = str(context["student_name"])

    existing = _wiki_paper_entries(student_name=student_name, query=query, limit=8)
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

    results = _wiki_paper_entries(student_name=student_name, query=query, limit=8)
    return {"results": results, "new_nodes_created": new_nodes}
