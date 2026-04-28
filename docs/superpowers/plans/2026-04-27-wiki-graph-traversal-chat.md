# Wiki Graph-Traversal Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Ask Monty's context gathering from keyword-matching to index-guided adaptive graph traversal so the chat leverages the wiki's linked structure.

**Architecture:** Two changes: (1) enrich `index.md` with one-line summaries from frontmatter so the LLM can navigate the wiki, (2) replace the flat keyword-matching `_gather_context()` with a two-phase retrieval pipeline: LLM selects pages from the index, then the system follows wiki links adaptively to expand context.

**Tech Stack:** Python, OpenAI SDK, python-frontmatter, existing wiki_writer.py + chat_service.py

**Spec:** `docs/superpowers/specs/2026-04-27-wiki-graph-traversal-chat-design.md`

---

### Task 1: Enrich `_write_root_index()` with frontmatter summaries

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py:65-109`

- [ ] **Step 1: Update behavioral node entries to include title, support_count, students_count**

Replace the behavioral node loop (lines 78-80) in `_write_root_index`:

```python
# Old:
for f in files:
    slug = f.stem
    sections.append(f"- [{slug}](behavioral/{ntype}/{f.name})\n")

# New:
for f in files:
    slug = f.stem
    try:
        meta = frontmatter.load(f).metadata
        title = meta.get("title", slug)
        sc = meta.get("support_count", 0)
        stc = meta.get("students_count", 0)
        sections.append(
            f"- [{slug}](behavioral/{ntype}/{f.name})"
            f" — {title} (support: {sc}, students: {stc})\n"
        )
    except Exception:
        sections.append(f"- [{slug}](behavioral/{ntype}/{f.name})\n")
```

- [ ] **Step 2: Update student entries to include severity, trend from profile frontmatter**

Replace the student loop (lines 88-91):

```python
# Old:
for sdir in student_dirs:
    display = sdir.name.replace("_", " ")
    inc_count = len(list((sdir / "incidents").glob("*.md"))) if (sdir / "incidents").exists() else 0
    sections.append(f"- [{display}](students/{sdir.name}/profile.md) — {inc_count} incident(s)\n")

# New:
for sdir in student_dirs:
    display = sdir.name.replace("_", " ")
    inc_count = len(list((sdir / "incidents").glob("*.md"))) if (sdir / "incidents").exists() else 0
    profile_path = sdir / "profile.md"
    severity = "unknown"
    trend = "unknown"
    if profile_path.exists():
        try:
            pmeta = frontmatter.load(profile_path).metadata
            severity = pmeta.get("current_severity", "unknown")
            trend = pmeta.get("trend", "unknown")
        except Exception:
            pass
    sections.append(
        f"- [{display}](students/{sdir.name}/profile.md)"
        f" — severity: {severity}, trend: {trend}, {inc_count} incident(s)\n"
    )
```

- [ ] **Step 3: Update research paper entries to include title, year, cited_by_count, fetched_for_query**

Replace the papers loop (lines 103-105):

```python
# Old:
for f in papers:
    sections.append(f"- [{f.stem}](sources/openalex/{f.name})\n")

# New:
for f in papers:
    try:
        meta = frontmatter.load(f).metadata
        title = meta.get("title", f.stem)
        year = meta.get("publication_year", "?")
        cited = meta.get("cited_by_count", 0)
        query = meta.get("fetched_for_query", "")
        query_short = query[:60] + "..." if len(query) > 60 else query
        sections.append(
            f"- [{f.stem}](sources/openalex/{f.name})"
            f' — "{title}" ({year}, cited {cited}x'
            f"{f', query: {query_short}' if query_short else ''})\n"
        )
    except Exception:
        sections.append(f"- [{f.stem}](sources/openalex/{f.name})\n")
```

- [ ] **Step 4: Verify the enriched index generates correctly**

Run from project root:

```bash
python3 -c "from intelligence.api.services.wiki_writer import update_indexes; update_indexes(); print(open('wiki/index.md').read()[:2000])"
```

Expected: index entries now show titles, support counts, severity, paper titles instead of bare slugs.

- [ ] **Step 5: Commit**

```bash
git add intelligence/api/services/wiki_writer.py
git commit -m "feat: enrich wiki index.md with frontmatter summaries for LLM retrieval"
```

---

### Task 2: Enrich `_write_behavioral_index()` with summaries and edge labels

**Files:**
- Modify: `intelligence/api/services/wiki_writer.py:112-138`

- [ ] **Step 1: Update behavioral node entries in `_write_behavioral_index`**

Replace the node loop (lines 126-127):

```python
# Old:
for f in files:
    sections.append(f"- [{f.stem}]({ntype}/{f.name})\n")

# New:
for f in files:
    try:
        meta = frontmatter.load(f).metadata
        title = meta.get("title", f.stem)
        sc = meta.get("support_count", 0)
        stc = meta.get("students_count", 0)
        sections.append(
            f"- [{f.stem}]({ntype}/{f.name})"
            f" — {title} (support: {sc}, students: {stc})\n"
        )
    except Exception:
        sections.append(f"- [{f.stem}]({ntype}/{f.name})\n")
```

- [ ] **Step 2: Update edge entries to include relationship labels**

Replace the edges loop (lines 132-134):

```python
# Old:
for f in edges:
    sections.append(f"- [{f.stem}](_edges/{f.name})\n")

# New:
for f in edges:
    try:
        meta = frontmatter.load(f).metadata
        src = meta.get("src_slug", "?")
        rel = meta.get("rel", "?")
        dst = meta.get("dst_slug", "?")
        sc = meta.get("support_count", 0)
        sections.append(
            f"- {src} —[{rel}]→ {dst}"
            f" (support: {sc})"
            f" [{f.stem}](_edges/{f.name})\n"
        )
    except Exception:
        sections.append(f"- [{f.stem}](_edges/{f.name})\n")
```

- [ ] **Step 3: Verify the enriched behavioral index generates correctly**

```bash
python3 -c "from intelligence.api.services.wiki_writer import update_indexes; update_indexes(); print(open('wiki/behavioral/_index.md').read()[:2000])"
```

Expected: node entries show titles/counts, edge entries show `src —[rel]→ dst (support: N)`.

- [ ] **Step 4: Commit**

```bash
git add intelligence/api/services/wiki_writer.py
git commit -m "feat: enrich behavioral _index.md with summaries and edge labels"
```

---

### Task 3: Implement index-guided page selection in chat_service.py

**Files:**
- Modify: `intelligence/api/services/chat_service.py`

- [ ] **Step 1: Add the page selection prompt and function**

Add after the existing `SYSTEM_PROMPT` constant (after line 26):

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add intelligence/api/services/chat_service.py
git commit -m "feat: add index-guided page selection for wiki chat"
```

---

### Task 4: Implement adaptive graph-traversal context gathering

**Files:**
- Modify: `intelligence/api/services/chat_service.py`

- [ ] **Step 1: Add the link extraction and expansion functions**

Add after `_select_pages`:

```python
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
```

- [ ] **Step 2: Replace `_gather_context` with the new two-phase retrieval**

Replace the entire `_gather_context` function with:

```python
def _gather_context(
    question: str,
    current_page_path: str | None = None,
    selected_text: str | None = None,
) -> str:
    """Build context via index-guided adaptive graph traversal."""
    parts: list[str] = []
    read_paths: set[str] = set()
    token_count = 0

    # 1. Current page context (if user is viewing one)
    if current_page_path:
        full_path = WIKI_ROOT / current_page_path
        if full_path.exists() and full_path.is_file():
            content = full_path.read_text(encoding="utf-8")[:3000]
            parts.append(f"## Currently viewing: {current_page_path}\n{content}")
            token_count += _estimate_tokens(content)
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
        page_tokens = _estimate_tokens(page_text)
        parts.append(f"## Page: {path_str_clean}\n{page_text}")
        select_tokens_used += page_tokens
        token_count += page_tokens
        read_paths.add(path_str_clean)

        # Collect link candidates from this page
        all_link_candidates.extend(_extract_link_candidates(content, meta))

    # 5. Adaptive expansion
    # Determine expansion budget based on how much the selected pages consumed
    if select_tokens_used < 4000:
        expansion_budget = 8000
        allow_2hop = True
    elif select_tokens_used < 8000:
        expansion_budget = 4000
        allow_2hop = False
    else:
        expansion_budget = 2000
        allow_2hop = False

    # Score candidates by reference count, deduplicate
    from collections import Counter
    candidate_counts = Counter(all_link_candidates)
    # Remove already-read pages
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
        page_tokens = _estimate_tokens(page_text)
        parts.append(f"## Linked: {candidate_clean}\n{page_text}")
        expansion_tokens_used += page_tokens
        token_count += page_tokens
        read_paths.add(candidate_clean)

        # Collect 2-hop candidates if budget allows
        if allow_2hop:
            hop2_candidates.extend(_extract_link_candidates(content, meta))

    # 2-hop expansion (only if adaptive budget allows)
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
            page_tokens = _estimate_tokens(page_text)
            parts.append(f"## Linked (2-hop): {candidate_clean}\n{page_text}")
            remaining -= page_tokens
            token_count += page_tokens
            read_paths.add(candidate_clean)

    return "\n\n".join(parts)
```

- [ ] **Step 3: Add the fallback keyword selector**

Add after `_extract_link_candidates`:

```python
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
                # Find the right subdirectory for this type
                for btype in ("setting_events", "antecedents", "behaviors",
                              "functions", "brain_states", "responses", "protective_factors"):
                    if ntype in btype or btype.startswith(ntype):
                        paths.append(f"behavioral/{btype}/{slug}.md")
                        break
        # Also check if a student is mentioned
        student = _detect_student_query(question)
        if student:
            sdir = f"students/{student.replace(' ', '_')}"
            paths.append(f"{sdir}/profile.md")
            paths.append(f"{sdir}/patterns.md")
        return paths
    finally:
        conn.close()
```

- [ ] **Step 4: Remove the old `import frontmatter` if missing, add it at the top**

Add `import frontmatter` to the imports at the top of `chat_service.py` (after `from pathlib import Path`). The file currently imports `from intelligence.api.services.wiki_paths import WIKI_ROOT` but does not import `frontmatter`. Add:

```python
import frontmatter
```

- [ ] **Step 5: Verify the chat service works end-to-end**

Start the API server and test:

```bash
uvicorn intelligence.api.main:app --port 8000 &
sleep 3
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What behavioral patterns involve frustration?"}' | head -c 500
```

Expected: streaming response that references specific behavioral nodes from the wiki.

- [ ] **Step 6: Commit**

```bash
git add intelligence/api/services/chat_service.py
git commit -m "feat: replace keyword matching with index-guided adaptive graph traversal in Ask Monty"
```

---

### Task 5: Clean up and final verification

**Files:**
- Modify: `intelligence/api/services/chat_service.py` (remove dead code)

- [ ] **Step 1: Remove unused imports**

The old `_gather_context` imported `Counter` inline. The new version imports it inline too (inside the function). Check for any other dead imports from the old keyword-matching code. The `_conn` import is still needed for `_fallback_keyword_select`.

- [ ] **Step 2: Regenerate indexes with enriched data**

```bash
python3 -c "from intelligence.api.services.wiki_writer import update_indexes; update_indexes(); print('done')"
```

- [ ] **Step 3: Test with a student-specific query**

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How is Mira Shah doing?"}' | head -c 500
```

Expected: response references Mira's profile, recent incidents, and linked behavioral nodes.

- [ ] **Step 4: Test with wiki page context**

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What does this pattern mean?", "current_page_path": "behavioral/behaviors/shutdown-stillness-avoidance.md"}' | head -c 500
```

Expected: response references the current page content plus linked nodes and papers.

- [ ] **Step 5: Final commit + push**

```bash
git add -A
git commit -m "chore: clean up chat_service after graph traversal upgrade"
git push origin main
```
