# Wiki Graph-Traversal Chat Design

Upgrade Ask Monty's context gathering from keyword-matching to index-guided adaptive graph traversal, inspired by [Karpathy's LLM-wiki concept](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The index serves as the primary retrieval mechanism. The LLM reads it, decides which pages to fetch, and the system follows wiki links adaptively to gather richer context.

## Problem

The current `chat_service._gather_context()` does SQL `LIKE %keyword%` matching on `behavioral_nodes`, reads matched files in isolation, and never follows links between pages. It treats the wiki as a flat search index.

The wiki is a linked knowledge structure. Incident files have `behavioral_refs` pointing to nodes. Edge files connect nodes with typed relationships. Research papers are linked from nodes. The chat service ignores all of this.

The `index.md` file is a flat list of slugs with no summaries, making it useless for LLM-guided page selection.

## Design

### 1. Enrich the index

Modify `_write_root_index()` in `wiki_writer.py` to read frontmatter from each file and include one-line summaries.

**Behavioral nodes:**
```markdown
- [avoidance-in-reading-corner](behavioral/behaviors/avoidance-in-reading-corner.md) — Avoidance and withdrawal; child moves away from interaction (support: 3, students: 2)
```

**Research papers:**
```markdown
- [W1556609206](sources/openalex/W1556609206.md) — "Investigating Young Children's Music-making Behavior" (2012, cited 3x, query: sensory processing attention drift)
```

**Students:**
```markdown
- [Mira Shah](students/Mira_Shah/profile.md) — severity: yellow, trend: stable, 12 incidents
```

**Behavioral index (`_write_behavioral_index`):** Include edge entries with relationship labels:
```markdown
- antecedents/mismatch-in-letter-sequence —[triggers]→ behaviors/pushes-tray-forward (support: 3)
```

Cost: reading frontmatter during index rebuild. The rebuild already touches every file, so this is negligible.

### 2. Index-guided adaptive retrieval

Replace `_gather_context()` in `chat_service.py` with a two-phase retrieval pipeline:

#### Phase 1: Page selection via LLM

1. Load `index.md` in full.
2. Send index + user question to a cheap/fast LLM call.
3. System prompt instructs the LLM to return a JSON array of 5-15 wiki file paths most likely to contain the answer.
4. Selection heuristics encoded in the prompt: prefer high support counts, papers whose titles match the topic, student profiles if the question names a student.

Page selection prompt:
```
You are a retrieval assistant for a Montessori behavioral knowledge wiki.
Given the wiki index below and the user's question, return a JSON array
of file paths to read. Select 5-15 pages most likely to contain or
contribute to the answer.

Prefer:
- Behavioral nodes with high support counts relevant to the question
- Research papers whose titles relate to the topic
- Student profiles/incidents if the question names a specific child
- Edge files that connect relevant behavioral patterns

Return ONLY a JSON array of path strings, nothing else.
Example: ["behavioral/behaviors/shutdown-stillness-avoidance.md", "sources/openalex/W1556609206.md"]
```

#### Phase 2: Read pages + adaptive expansion

**Step 1 — Read selected pages.** Read the full markdown content of each LLM-selected path. Accumulate into a context string. Stop at ~8K tokens (estimated by character count / 4).

**Step 2 — Collect 1-hop link candidates.** Scan the content and frontmatter of all read pages for outgoing references:
- `behavioral_refs` arrays in incident frontmatter
- `src_slug` / `dst_slug` in edge frontmatter
- `[[wikilink]]` and `[text](relative-path)` in markdown body
- `fetched_for_student` in research paper frontmatter (link back to student)
- Any slug mentioned in a node's `related_nodes` frontmatter field

Deduplicate against already-read pages. Score candidates by reference count (how many read pages link to them).

**Step 3 — Adaptive budget.** Calculate remaining token budget:
- If selected pages consumed < 4K tokens (sparse wiki / few matches): expansion budget = 8K tokens, allow 2-hop (follow links from expansion pages too)
- If selected pages consumed 4K-8K tokens (normal): expansion budget = 4K tokens, 1-hop only
- If selected pages consumed > 8K tokens (dense result): expansion budget = 2K tokens, 1-hop only

Read expansion candidates in descending reference-count order until the expansion budget is exhausted.

**Step 4 — Assemble context.** Concatenate:
1. Currently viewed page content (if user is on a wiki page), truncated to 3K chars
2. User's selected text (if any), truncated to 500 chars
3. All read pages, each prefixed with `## Page: <path>`
4. Total context target: ~16K tokens max

#### Phase 3: Answer

Send assembled context + conversation history (last 10 turns) + question to the LLM. Stream the response.

### 3. Existing behavior preserved

- Student-specific queries still load the student's profile + recent incidents. The page selection LLM will naturally select these when a student name appears in the question.
- Current page context and selected text are still prepended.
- Conversation history (last 10 turns) is still included.
- The anonymization rules in the system prompt are unchanged.

## Files modified

| File | Change |
|------|--------|
| `intelligence/api/services/wiki_writer.py` | `_write_root_index()`: read frontmatter, include summaries. `_write_behavioral_index()`: include edge entries with labels. |
| `intelligence/api/services/chat_service.py` | Replace `_gather_context()` with index-guided two-phase retrieval. Add `_select_pages()` for the LLM page selection call. Add `_collect_link_candidates()` for 1-hop/2-hop expansion. |

No new files. No new dependencies.

## Token budget summary

| Component | Budget |
|-----------|--------|
| Index (always loaded) | Unlimited (navigation layer) |
| Selected pages | ~8K tokens |
| Adaptive expansion | 2K-8K tokens (inversely proportional to selected page volume) |
| Current page + selection | ~3.5K tokens |
| Conversation history | ~2K tokens (last 10 turns) |
| Total context ceiling | ~16K tokens |

## Edge cases

- **Empty wiki:** Index is nearly empty, page selection returns few/no paths. The answer call gets minimal context and the LLM says it doesn't have enough data. This is correct behavior.
- **LLM returns invalid JSON from page selection:** Fall back to the current keyword-matching approach as a degraded path.
- **LLM returns paths that don't exist on disk:** Skip them silently, log a warning.
- **Very large wiki (2,400+ files, 10MB+):** Index may be 25K+ tokens. This fits in context. Page selection keeps reads bounded regardless of wiki size. The adaptive budget prevents context overflow.
- **No OpenAI key:** Return a message saying Ask Monty requires an API key. Same as current behavior.
