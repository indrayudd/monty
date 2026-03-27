"""Seed student_literature by reading aggregated profiles, generating search queries via LLM, and fetching papers from OpenAlex."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# load OpenAlex key from contracts/.env
_env_path = Path(__file__).resolve().parents[2] / "contracts" / ".env"
if _env_path.exists():
    for line in _env_path.read_text().strip().splitlines():
        key, _, val = line.partition("=")
        if key.strip() and val.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()

# also check root .env
_root_env = Path(__file__).resolve().parents[2] / ".env"
if _root_env.exists():
    for line in _root_env.read_text().strip().splitlines():
        key, _, val = line.partition("=")
        if key.strip() and val.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()

from intelligence.api.services.ghost_client import (
    ensure_literature_table,
    get_all_profiles,
    insert_literature,
)
from intelligence.api.services.llm_service import generate_search_queries

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from notes_streamer.literature_scraping.api_usage_example import (
    OpenAlexClient,
    extract_abstract_text,
    extract_basic_metadata,
    score_work_for_selection,
)


def run():
    openalex_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not openalex_key:
        print("error: OPENALEX_API_KEY is required (set in .env or contracts/.env)", file=sys.stderr)
        return 1

    openalex = OpenAlexClient(api_key=openalex_key, user_agent="monty-literature/0.1")

    ensure_literature_table()
    profiles = get_all_profiles()
    print(f"Found {len(profiles)} student profiles.\n")

    for i, profile in enumerate(profiles, 1):
        name = profile["student_name"]
        patterns = profile.get("latest_patterns") or ""
        summary = profile.get("latest_summary") or ""
        severity = profile.get("current_severity") or "green"

        if not patterns and not summary:
            print(f"[{i}/{len(profiles)}] {name} — skipping (no patterns/summary)")
            continue

        print(f"[{i}/{len(profiles)}] {name} ({severity}) ... ", end="", flush=True)

        # Step 1: LLM generates search queries from aggregated profile
        result = generate_search_queries(name, patterns, summary, severity)
        queries = result.get("queries", [])
        print(f"{len(queries)} queries", flush=True)

        # Step 2: search OpenAlex for each query, collect top papers
        for query in queries:
            print(f"  -> searching: {query}")
            try:
                search_resp = openalex.search_works(
                    topic_query=query,
                    per_page=5,
                    extra_filter="open_access.is_oa:true",
                    select="id,display_name,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_location,best_oa_location,open_access,has_content,ids",
                )
            except Exception as exc:
                print(f"     OpenAlex error: {exc}")
                continue

            candidates = search_resp.get("results", [])
            if not candidates:
                print("     no results")
                continue

            # Pick top 2 by score
            ranked = sorted(candidates, key=score_work_for_selection, reverse=True)
            for work in ranked[:2]:
                meta = extract_basic_metadata(work)
                openalex_id = meta.get("openalex_id") or ""
                if not openalex_id:
                    continue

                abstract = extract_abstract_text(work)
                authors_str = ", ".join(meta.get("authors", []))
                title = meta.get("title") or "Untitled"

                insert_literature({
                    "student_name": name,
                    "search_query": query,
                    "openalex_id": openalex_id,
                    "title": title,
                    "authors": authors_str,
                    "publication_year": meta.get("publication_year"),
                    "cited_by_count": meta.get("cited_by_count", 0),
                    "abstract": abstract[:2000] if abstract else None,
                    "landing_page_url": meta.get("landing_page_url"),
                    "relevance_summary": f"Matched for profile pattern: {patterns[:200]}",
                })
                print(f"     + {title[:70]}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
