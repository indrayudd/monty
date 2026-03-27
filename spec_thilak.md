# PEP OS — Thilak's Spec (Intelligence API + Frontend)

> Owner: **Thilak**
> Layers: Intelligence, Frontend
> Directories: `intelligence/`, `frontend/`

---

## 1. Intelligence API (Python / FastAPI)

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/flags` | GET | All active flags, sorted by severity |
| `/api/flags/{student_id}` | GET | Flags for a specific student |
| `/api/insights/{student_id}` | GET | LLM-generated interpretation of student's flags + KG context |
| `/api/suggestions/{student_id}` | GET | Actionable suggestions for educators |
| `/api/kg/query` | POST | Proxy to Indro's KG agent with self-improvement wrapper |
| `/api/health` | GET | Health check |

### Services

| Service | File | Purpose |
|---------|------|---------|
| Ghost Client | `services/ghost_client.py` | Ghost SDK wrapper — reads from both Ghost DB instances |
| LLM Service | `services/llm_service.py` | Claude API calls for interpretations + suggestions |
| Self-Improve | `services/self_improve.py` | Prompt refinement engine |

### Request Flow
```
Frontend → Intelligence API → Ghost DB (read flags/KG)
                            → Claude LLM (generate insights)
                            → KG Agent (on-demand research if needed)
                            → Response (flags + interpretation + suggestions)
```

---

## 2. Self-Improvement Mechanism

### Prompt Refinement Loop
1. Each LLM call logs: `prompt_version`, `input_context`, `output`, `timestamp`, `quality_score`
2. Scoring heuristic evaluates output quality:
   - Relevance: Does the output address the specific student's flags?
   - Actionability: Are suggestions concrete and implementable?
   - Specificity: Does it reference relevant research from the KG?
3. When average quality drops below threshold → analyze recent low-scoring outputs → refine prompts
4. Store prompt versions in `prompts/` directory for rollback

### On-Demand KG Enrichment
- When generating insights/suggestions, if the LLM identifies knowledge gaps (e.g., unfamiliar flag patterns):
  1. Formulate a research query
  2. Call Indro's KG agent: `POST KG_AGENT_URL/api/kg-agent/query`
  3. Incorporate new KG nodes into the current response
  4. Future requests benefit from the expanded KG

---

## 3. Frontend (Next.js)

### Dashboard Layout
Single-page dashboard with a student selector and 3 panels:

| Panel | Component | Data Source |
|-------|-----------|-------------|
| Panel 1 — Flag Alerts | `FlagAlerts.tsx` | `GET /api/flags` or `/api/flags/{student_id}` |
| Panel 2 — Interpretations | `Interpretations.tsx` | `GET /api/insights/{student_id}` |
| Panel 3 — Suggestions | `Suggestions.tsx` | `GET /api/suggestions/{student_id}` |

### Panel Details

**Panel 1 — Flag Alerts**
- Severity-sorted list (critical → high → medium → low)
- Color-coded by severity
- Filterable by flag type (attendance, engagement, mood, behavior)
- Shows: student name, flag type, severity badge, description, timestamp

**Panel 2 — Interpretations**
- LLM-generated narrative analyzing the student's behavioral patterns
- Cross-references with KG research insights
- Shows confidence indicators
- Updates when new flags arrive

**Panel 3 — Suggestions**
- Actionable recommendations for educators
- Backed by KG research (citations to arxiv papers when available)
- Prioritized by urgency
- Each suggestion includes: action, rationale, expected outcome

---

## 4. Mock Data (for independent development)

Create mock fixtures in `intelligence/api/mocks/` matching the schemas from `spec_integration.md`:
- `mock_students.json`
- `mock_flags.json`
- `mock_notes.json` (id, name, body)
- `mock_knowledge_graph.json`

The Ghost Client service should:
- Try Ghost DB first
- Fall back to mock data if Ghost DB is unavailable or empty
- Log which mode it's running in

This lets the full stack work before Indro's services are ready.

---

## 5. Directory Structure

```
intelligence/
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── routes/
│   │   ├── flags.py
│   │   ├── insights.py
│   │   └── suggestions.py
│   ├── services/
│   │   ├── ghost_client.py
│   │   ├── llm_service.py
│   │   └── self_improve.py
│   ├── prompts/
│   │   └── base_prompts.py  # Versioned prompt templates
│   └── mocks/
│       ├── mock_students.json
│       ├── mock_flags.json
│       ├── mock_notes.json
│       └── mock_knowledge_graph.json
└── requirements.txt

frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx         # Dashboard page
│   ├── components/
│   │   ├── FlagAlerts.tsx
│   │   ├── Interpretations.tsx
│   │   ├── Suggestions.tsx
│   │   └── StudentSelector.tsx
│   └── lib/
│       └── api.ts           # Fetch wrapper for Intelligence API
├── package.json
└── next.config.js
```

---

## 6. Deliverables Checklist

- [ ] FastAPI server with all 6 endpoints working
- [ ] Self-improvement loop with prompt versioning and quality scoring
- [ ] Next.js frontend with 3 panels rendering data
- [ ] Student selector component
- [ ] Mock data fallback working independently
- [ ] Can consume Indro's Ghost DB data when available
- [ ] Can trigger Indro's KG agent endpoint on-demand

---

## 7. Integration Notes

- **Do not modify** files in `agents/` or `data/` — those are Indro's
- **Schema changes**: If you need a schema change, update `contracts/schemas.json` and notify Indro
- **Env vars needed**: `ANTHROPIC_API_KEY`, `GHOST_DB_URL`, `GHOST_DB_API_KEY`, `KG_AGENT_URL`
- **Ports**: Intelligence API on 8000, Frontend on 3000
