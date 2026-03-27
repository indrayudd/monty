from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from intelligence.api.services.demo_runtime import bootstrap_demo, get_demo_overview
from intelligence.api.services.ghost_client import (
    count_notes,
    ensure_agent_tables,
    ensure_notes_table,
    get_alerts,
    get_all_profiles,
    get_knowledge_graph_entries,
    get_personality_graph,
    get_runtime_state,
    get_student_literature,
    get_student_profile,
    get_student_snapshots,
)
from intelligence.api.services.kg_agent import query_knowledge_graph
from intelligence.api.services.self_improve import run_agent_cycle


class AgentRunRequest(BaseModel):
    force_full: bool = False
    verbose: bool = False


class KGQueryRequest(BaseModel):
    query: str
    context: dict[str, Any] | None = None


class DemoBootstrapRequest(BaseModel):
    reset: bool = False


app = FastAPI(title="Monty Intelligence API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_agent_tables()
    ensure_notes_table()
    if os.environ.get("MONTY_ENABLE_DEMO_RUNTIME", "1") == "1" and count_notes() == 0:
        bootstrap_demo(reset=False)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "monty-intelligence"}


@app.get("/api/flags")
def all_flags():
    profiles = get_all_profiles()
    return {"students": profiles}


@app.get("/api/flags/{student_name}")
def student_flags(student_name: str):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    snapshots = get_student_snapshots(student_name)
    return {"profile": profile, "snapshots": snapshots}


@app.get("/api/insights/{student_name}")
def student_insights(student_name: str):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {
        "student_name": student_name,
        "current_severity": profile["current_severity"],
        "previous_severity": profile["previous_severity"],
        "trend": profile["trend"],
        "assessment_count": profile["assessment_count"],
        "summary": profile["latest_summary"],
        "behavioral_patterns": profile["latest_patterns"],
    }


@app.get("/api/suggestions/{student_name}")
def student_suggestions(student_name: str):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {
        "student_name": student_name,
        "severity": profile["current_severity"],
        "trend": profile["trend"],
        "suggestions": profile["latest_suggestions"],
    }


@app.get("/api/literature/{student_name}")
def student_literature(student_name: str):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    papers = get_student_literature(student_name)
    return {
        "student_name": student_name,
        "severity": profile["current_severity"],
        "behavioral_patterns": profile["latest_patterns"],
        "papers": papers,
    }


@app.get("/api/alerts")
def all_alerts(status: str | None = "open"):
    return {"alerts": get_alerts(status=status)}


@app.get("/api/alerts/{student_name}")
def student_alerts(student_name: str, status: str | None = "open"):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {"student_name": student_name, "alerts": get_alerts(student_name=student_name, status=status)}


@app.get("/api/personality-graph/{student_name}")
def student_personality_graph(student_name: str):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {"student_name": student_name, "facets": get_personality_graph(student_name)}


@app.get("/api/knowledge-graph/{student_name}")
def student_knowledge_graph(student_name: str, query: str | None = None):
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {
        "student_name": student_name,
        "results": get_knowledge_graph_entries(student_name=student_name, query=query or profile.get("latest_patterns"), limit=12),
    }


@app.get("/api/agent/status")
def agent_status():
    return {
        "runtime": get_runtime_state(),
        "profile_count": len(get_all_profiles()),
        "open_alerts": len(get_alerts(status="open")),
    }


@app.post("/api/agent/run-cycle")
def run_cycle(request: AgentRunRequest):
    return run_agent_cycle(force_full=request.force_full, verbose=request.verbose)


@app.post("/api/kg/query")
def kg_query(request: KGQueryRequest):
    return query_knowledge_graph(request.query, request.context)


@app.post("/api/demo/bootstrap")
def demo_bootstrap(request: DemoBootstrapRequest):
    return bootstrap_demo(reset=request.reset)


@app.get("/api/demo/overview")
def demo_overview():
    return get_demo_overview()
