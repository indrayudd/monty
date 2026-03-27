# PEP OS — Indro's Spec (Data + Agents + Storage)

> Owner: **Indro**
> Layers: Data, Agent, Storage
> Directories: `agents/`, `data/`

---

## 1. Data Layer

### Synthetic Student Data Generator
- Generate realistic student profiles with behavioral/wellbeing attributes
- Each student has: name, cohort, enrollment date
- Output feeds into the Seed Agent

### arxiv API Integration
- Fetch papers related to: student wellbeing, pedagogy, behavioral science, educational interventions
- Feed paper metadata + abstracts into the KG Agent

---

## 2. Agent Layer

### Seed Agent
Generates student data with behavioral/wellbeing flags and writes to Ghost DB.

**Writes to these Ghost DB collections (schemas in `spec_integration.md`):**
- `students` — student profiles
- `flags` — behavioral/wellbeing flags with severity levels
- `notes` — contextual notes about students

**Flag types to generate:**
| Type | Examples |
|------|----------|
| `attendance` | Missed 3+ classes this week, chronic tardiness |
| `engagement` | Stopped participating in discussions, incomplete assignments |
| `mood` | Reported anxiety, visible distress noted by peers |
| `behavior` | Disruptive in class, social withdrawal, sudden grade drops |

**Severity levels:** `low`, `medium`, `high`, `critical`

### KG Agent (Self-Improving)
Autonomously fetches arxiv papers, extracts insights, and builds a knowledge graph.

**Writes to Ghost DB collection:**
- `knowledge_graph` — extracted insights with topics, source URLs, confidence scores

**Self-improvement behavior:**
- Runs on a schedule (or continuously) without human intervention
- Each cycle: fetch new papers → extract insights → add to KG → identify gaps → refine search queries
- The KG grows over time as the agent discovers new research areas
- This is the core "self-improving" criterion for hackathon judging

---

## 3. Storage Layer (Ghost DB)

Set up two Ghost DB instances at [ghost.build](https://ghost.build):

| Instance | Collections | Purpose |
|----------|------------|---------|
| Instance 1 | `students`, `flags`, `notes` | Student behavioral data |
| Instance 2 | `knowledge_graph` | Research knowledge graph |

**All schemas must match `spec_integration.md` exactly.** Thilak's Intelligence API reads from these directly via Ghost SDK.

---

## 4. KG Agent Trigger Server

Thilak's Intelligence API needs to trigger on-demand KG research. Expose this endpoint:

```
POST http://localhost:5001/api/kg-agent/query
Content-Type: application/json

Request body:
{
  "query": "string (natural language research query)",
  "context": {} (optional — student flags, topics for context)
}

Response:
{
  "results": [ ...knowledge_graph objects... ],
  "new_nodes_created": 3
}
```

Run this server from `agents/server.py` on port **5001**.

---

## 5. Environment Setup

Add these to the shared `.env` file:

```
GHOST_DB_URL=<your ghost.build URL>
GHOST_DB_API_KEY=<your API key>
KG_AGENT_URL=http://localhost:5001
```

---

## 6. Directory Structure

```
agents/
├── seed_agent/          # Synthetic student data → Ghost DB
├── kg_agent/            # arxiv → KG → Ghost DB (self-improving)
└── server.py            # HTTP endpoint for on-demand KG queries

data/
├── synthetic/           # Raw synthetic data generation
└── arxiv/               # arxiv API client
```

---

## 7. Deliverables Checklist

- [ ] Seed agent populating Ghost DB with student data + flags
- [ ] KG agent autonomously fetching/processing arxiv papers
- [ ] Ghost DB schemas match `spec_integration.md` contracts
- [ ] KG agent trigger endpoint running on port 5001
- [ ] Ghost DB connection credentials added to `.env`
- [ ] Self-improvement loop visible (KG grows over time, search queries refine)

---

## 8. Integration Notes

- **Do not modify** files in `intelligence/` or `frontend/` — those are Thilak's
- **Schema changes**: If you need to change a Ghost DB schema, update `contracts/schemas.json` first and notify Thilak
- **Testing**: Once your agents are running, Thilak's stack will automatically switch from mock data to your live Ghost DB data
