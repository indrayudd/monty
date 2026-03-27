# PEP OS — Integration Contract

> Shared between **Indro** and **Thilak**
> This is the source of truth for all data shapes and API contracts between the two workstreams.

---

## A. Ghost DB Collection Schemas

Indro writes to these collections. Thilak reads from them via Ghost SDK.

### `students`
```json
{
  "id": "string (uuid)",
  "name": "string",
  "cohort": "string",
  "created_at": "ISO8601 (e.g. 2026-03-27T10:00:00Z)"
}
```

### `flags`
```json
{
  "id": "string (uuid)",
  "student_id": "string (references students.id)",
  "type": "attendance | engagement | mood | behavior",
  "severity": "low | medium | high | critical",
  "description": "string",
  "source": "string (name of the agent that raised the flag)",
  "created_at": "ISO8601",
  "resolved": false
}
```

### `notes`
```json
{
  "id": "string (uuid)",
  "name": "string (student name)",
  "body": "string (teacher's note content)"
}
```

### `knowledge_graph`
```json
{
  "id": "string (uuid)",
  "topic": "string",
  "source_url": "string (arxiv paper URL)",
  "insights": ["string", "string"],
  "related_topics": ["string", "string"],
  "confidence": 0.85,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## B. KG Agent Trigger API

Indro exposes this endpoint. Thilak's Intelligence API calls it for on-demand research.

```
POST http://localhost:5001/api/kg-agent/query
Content-Type: application/json
```

**Request:**
```json
{
  "query": "effective interventions for student attendance drops",
  "context": {
    "student_flags": ["attendance", "engagement"],
    "severity": "high"
  }
}
```

**Response (200):**
```json
{
  "results": [
    {
      "id": "uuid",
      "topic": "attendance intervention strategies",
      "source_url": "https://arxiv.org/abs/2401.12345",
      "insights": [
        "Early warning systems reduce dropout by 15-20%",
        "Peer mentoring programs show significant improvement in attendance"
      ],
      "related_topics": ["peer mentoring", "early warning systems"],
      "confidence": 0.82,
      "created_at": "2026-03-27T10:30:00Z",
      "updated_at": "2026-03-27T10:30:00Z"
    }
  ],
  "new_nodes_created": 1
}
```

---

## C. Environment Variables

Shared `.env` file in repo root (gitignored). Use `.env.example` as template.

```bash
# === Indro fills these ===
GHOST_DB_URL=             # ghost.build instance URL
GHOST_DB_API_KEY=         # ghost.build API key

# KG Agent trigger server
KG_AGENT_URL=http://localhost:5001

# === Thilak fills these ===
ANTHROPIC_API_KEY=        # Claude API key

# Ports
INTELLIGENCE_API_PORT=8000
FRONTEND_PORT=3000
```

---

## D. Directory Structure (No Overlap)

```
monty/
├── agents/                  # INDRO ONLY
│   ├── seed_agent/
│   ├── kg_agent/
│   └── server.py
├── data/                    # INDRO ONLY
│   ├── synthetic/
│   └── arxiv/
├── intelligence/            # THILAK ONLY
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── prompts/
│   │   └── mocks/
│   └── requirements.txt
├── frontend/                # THILAK ONLY
│   ├── src/
│   ├── package.json
│   └── next.config.js
├── contracts/               # SHARED — source of truth
│   ├── schemas.json
│   └── kg_agent_api.yaml
├── spec_indro.md            # Indro's spec
├── spec_thilak.md           # Thilak's spec
├── spec_integration.md      # This file
├── .env.example
└── README.md
```

**Rule: Never modify files in the other person's directories.**

---

## E. Integration Checklist

Run through this when both sides are ready to connect:

- [ ] `.env` has all values filled in
- [ ] Ghost DB is reachable from Thilak's machine (`GHOST_DB_URL` + `GHOST_DB_API_KEY`)
- [ ] Ghost DB has data matching the schemas above
- [ ] KG agent trigger endpoint responds: `curl -X POST http://localhost:5001/api/kg-agent/query -H 'Content-Type: application/json' -d '{"query":"test"}'`
- [ ] Intelligence API reads live Ghost DB data: `curl http://localhost:8000/api/flags`
- [ ] Frontend renders live data from Intelligence API: open `http://localhost:3000`
- [ ] End-to-end KG query: Frontend → Intelligence API → KG Agent → Ghost DB → back

---

## F. Schema Change Protocol

If either person needs to change a schema:

1. Update `contracts/schemas.json` with the new shape
2. Notify the other person immediately
3. Both update their code to match
4. Do NOT change Ghost DB data shapes without updating the contract first

---

## G. Merge Workflow

- Both work on `main` branch — directory isolation prevents conflicts
- Pull before pushing
- If conflict arises in shared files (`contracts/`, `.env.example`, spec files), coordinate via message
- When Indro's agents are running and Ghost DB is populated, Thilak's stack switches from mock data to live data automatically
