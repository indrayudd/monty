from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from intelligence.api.services.ghost_client import ensure_agent_tables
from intelligence.api.services.kg_agent import query_knowledge_graph


class KGAgentRequest(BaseModel):
    query: str
    context: dict[str, Any] | None = None


app = FastAPI(title="Monty KG Agent", version="0.2.0")


@app.on_event("startup")
def startup() -> None:
    ensure_agent_tables()


@app.get("/health")
def health():
    return {"status": "ok", "service": "monty-kg-agent"}


@app.post("/api/kg-agent/query")
def kg_agent_query(request: KGAgentRequest):
    return query_knowledge_graph(request.query, request.context)
