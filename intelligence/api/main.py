from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from intelligence.api.services.demo_runtime import bootstrap_demo, get_demo_overview, reset_demo, start_demo, stop_demo
from intelligence.api.services.ghost_client import (
    _conn,
    ensure_agent_tables,
    ensure_notes_table,
    get_alerts,
    get_all_profiles,
    get_runtime_state,
    get_student_literature,
    get_student_profile,
    get_student_snapshots,
    list_behavioral_nodes,
    list_behavioral_edges,
    list_student_incidents,
    list_curiosity_events,
    get_runtime_overrides,
    set_runtime_overrides,
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


# /api/personality-graph/{name} and /api/knowledge-graph/{name} removed in Phase 5b.
# Replaced by /api/student-graph/{name} (per-student incidents + refs) and
# /api/behavioral-graph (anonymized cross-student KG).


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


@app.post("/api/demo/start")
def demo_start(request: DemoBootstrapRequest):
    return start_demo(reset=request.reset)


@app.post("/api/demo/reset")
def demo_reset():
    return reset_demo()


@app.post("/api/demo/stop")
def demo_stop():
    return stop_demo()


@app.get("/api/demo/overview")
def demo_overview():
    return get_demo_overview()


# ── Phase 0: empty/index-backed endpoints. Real behavior wired in Phases 1-3. ──

@app.get("/api/behavioral-graph")
def behavioral_graph(min_support: int = 1):
    nodes = list_behavioral_nodes()
    edges = list_behavioral_edges(min_support=min_support)
    return {"nodes": nodes, "edges": edges}


@app.get("/api/student-graph/{student_name}")
def student_graph(student_name: str, limit: int = 50):
    incidents = list_student_incidents(student_name, limit=limit)
    return {"student_name": student_name, "incidents": incidents}


@app.get("/api/student-graph/{student_name}/research")
def student_graph_research(student_name: str):
    # Phase 0: returns existing literature rows. Phase 3 enriches via wiki sources/openalex/.
    return {"student_name": student_name, "papers": get_student_literature(student_name)}


@app.get("/api/personas")
def personas():
    from notes_streamer.persona_engine import list_personas
    try:
        return {"personas": list_personas(), "overrides": get_runtime_overrides()}
    except NotImplementedError:
        return {"personas": [], "overrides": get_runtime_overrides(), "stub": True}


class PersonaUpdate(BaseModel):
    slider: float | None = None
    flavor_override: str | None = None
    activity_weight: float | None = None


@app.patch("/api/personas/{student_name}")
def update_persona(student_name: str, payload: PersonaUpdate):
    overrides = get_runtime_overrides()
    student_block = overrides.get(student_name, {})
    if payload.slider is not None:
        student_block["slider"] = payload.slider
    if payload.flavor_override is not None:
        student_block["flavor_override"] = payload.flavor_override
    if payload.activity_weight is not None:
        student_block["activity_weight"] = payload.activity_weight
    overrides[student_name] = student_block
    set_runtime_overrides(overrides)
    return {"student_name": student_name, "overrides": student_block}


class InjectRequest(BaseModel):
    flavor: str  # "neutral" | "problematic" | "emergency" | "surprise"


@app.post("/api/personas/{student_name}/inject")
def inject_persona(student_name: str, payload: InjectRequest):
    overrides = get_runtime_overrides()
    block = overrides.get(student_name, {})
    block["inject_next"] = payload.flavor
    overrides[student_name] = block
    set_runtime_overrides(overrides)
    return {"student_name": student_name, "inject_next": payload.flavor}


class InteractRequest(BaseModel):
    a: str
    b: str
    scene_hint: str | None = None


@app.post("/api/personas/interact")
def interact_personas(payload: InteractRequest):
    overrides = get_runtime_overrides()
    for name in (payload.a, payload.b):
        block = overrides.get(name, {})
        block["interact_with"] = payload.b if name == payload.a else payload.a
        if payload.scene_hint:
            block["interact_scene_hint"] = payload.scene_hint
        overrides[name] = block
    set_runtime_overrides(overrides)
    return {"a": payload.a, "b": payload.b}


class NextNoteRequest(BaseModel):
    student_name: str


@app.post("/api/persona/next-note")
def persona_next_note(payload: NextNoteRequest):
    from notes_streamer.persona_engine import generate_next_note, PersonaOverrides
    overrides = get_runtime_overrides().get(payload.student_name, {})
    po = PersonaOverrides(**{k: v for k, v in overrides.items() if k in PersonaOverrides.__dataclass_fields__})
    try:
        note = generate_next_note(payload.student_name, overrides=po)
        return note
    except NotImplementedError:
        raise HTTPException(503, "persona_engine not yet implemented (Phase 1)")


@app.get("/api/runtime/research-edges")
def research_edges():
    """Return recent research edge discovery checks."""
    from intelligence.api.services.ghost_client import _fetchall
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT slug_a, slug_b, checked_at, found_connection "
            "FROM research_edge_checks ORDER BY checked_at DESC LIMIT 50"
        )
        rows = _fetchall(cur)
    finally:
        conn.close()
    return {"checks": rows}


@app.get("/api/curiosity/events")
def curiosity_events_endpoint(limit: int = 50):
    return {"events": list_curiosity_events(limit=limit)}


class CuriosityWeightUpdate(BaseModel):
    novelty: float | None = None
    recurrence_gap: float | None = None
    cross_student: float | None = None
    surprise: float | None = None
    severity_weight: float | None = None
    recency: float | None = None


@app.patch("/api/runtime/curiosity-weights")
def update_curiosity_weights(payload: CuriosityWeightUpdate):
    overrides = get_runtime_overrides()
    weights = overrides.get("_curiosity_weights", {})
    for k, v in payload.dict(exclude_none=True).items():
        weights[k] = v
    overrides["_curiosity_weights"] = weights
    set_runtime_overrides(overrides)
    return {"curiosity_weights": weights}


@app.post("/api/runtime/pause")
def pause_streamer():
    overrides = get_runtime_overrides()
    overrides["_paused"] = True
    set_runtime_overrides(overrides)
    return {"paused": True}


@app.post("/api/runtime/resume")
def resume_streamer():
    overrides = get_runtime_overrides()
    overrides["_paused"] = False
    set_runtime_overrides(overrides)
    return {"paused": False}


@app.get("/api/notes/recent")
def recent_notes(limit: int = 5):
    """Return the last N ingested observations for the God Mode live feed."""
    from intelligence.api.services.ghost_client import _conn
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, body, inserted_at FROM ingested_observations "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
        return {"notes": rows}
    finally:
        conn.close()


class NoteCadenceUpdate(BaseModel):
    cadence: float  # seconds between notes (0 = default random 2-8s)


@app.patch("/api/runtime/note-cadence")
def update_note_cadence(payload: NoteCadenceUpdate):
    overrides = get_runtime_overrides()
    overrides["_note_cadence"] = max(0, payload.cadence)
    set_runtime_overrides(overrides)
    return {"note_cadence": overrides["_note_cadence"]}


@app.get("/api/runtime/note-cadence")
def get_note_cadence():
    overrides = get_runtime_overrides()
    return {"note_cadence": float(overrides.get("_note_cadence", 0))}


@app.post("/api/curiosity/recompute/{slug}")
def curiosity_recompute(slug: str):
    from intelligence.api.services.curiosity import compute_factors
    try:
        factors = compute_factors(slug)
        return {"slug": slug, "factors": factors.to_dict(), "score": factors.score()}
    except NotImplementedError:
        raise HTTPException(503, "curiosity.compute_factors not yet implemented (Phase 3)")


@app.post("/api/curiosity/investigate/{slug}")
def curiosity_investigate(slug: str):
    try:
        from intelligence.api.services.curiosity import evaluate_gate
        result = evaluate_gate(slug)
        return result
    except NotImplementedError:
        raise HTTPException(503, "curiosity.evaluate_gate not yet implemented (Phase 3)")


@app.get("/api/wiki/tree")
def wiki_tree():
    from intelligence.api.services.wiki_paths import WIKI_ROOT
    tree: list[dict] = []
    for path in sorted(WIKI_ROOT.rglob("*.md")):
        rel = path.relative_to(WIKI_ROOT).as_posix()
        tree.append({"path": rel, "mtime": path.stat().st_mtime})
    return {"root": str(WIKI_ROOT), "files": tree}


@app.get("/api/wiki/page")
def wiki_page(path: str):
    from intelligence.api.services.wiki_paths import WIKI_ROOT
    target = (WIKI_ROOT / path).resolve()
    if not str(target).startswith(str(WIKI_ROOT.resolve())):
        raise HTTPException(400, "path traversal blocked")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, f"no such wiki page: {path}")
    raw = target.read_text(encoding="utf-8")
    # Frontmatter parsing — Phase 2 will add backlinks computation. Phase 0 returns raw.
    try:
        import frontmatter
        post = frontmatter.loads(raw)
        return {"path": path, "frontmatter": post.metadata, "body": post.content, "raw": raw}
    except Exception:
        return {"path": path, "frontmatter": {}, "body": raw, "raw": raw}


@app.post("/api/wiki/reindex")
def wiki_reindex():
    try:
        from intelligence.api.services.wiki_indexer import full_rebuild
        return full_rebuild()
    except NotImplementedError:
        raise HTTPException(503, "wiki_indexer.full_rebuild not yet implemented (Phase 2)")


class ChatRequest(BaseModel):
    question: str
    history: list[dict] | None = None
    current_page_path: str | None = None
    selected_text: str | None = None


@app.post("/api/chat")
def chat(request: ChatRequest):
    from intelligence.api.services.chat_service import stream_chat

    def generate():
        for chunk in stream_chat(
            question=request.question,
            history=request.history,
            current_page_path=request.current_page_path,
            selected_text=request.selected_text,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/api/admin/purge")
def admin_purge():
    """Nuclear option: wipe all DB state + wiki generated content. Keeps personas + skeleton."""
    import shutil
    from intelligence.api.services.wiki_paths import WIKI_ROOT, BEHAVIORAL_TYPES

    # 1. Delete all data from all tables (single DB now)
    conn = _conn()
    try:
        cur = conn.cursor()
        for table in [
            "ingested_observations",
            "behavioral_nodes",
            "behavioral_edges",
            "student_incidents",
            "student_profiles_index",
            "curiosity_events",
            "student_profiles",
            "profile_snapshots",
            "student_literature",
            "student_alerts",
            "agent_actions",
            "agent_runtime_state",
            "research_edge_checks",
        ]:
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()

    # 2. Wipe wiki generated content (keep skeleton + personas)
    for bt in BEHAVIORAL_TYPES:
        d = WIKI_ROOT / "behavioral" / bt
        for f in d.glob("*.md"):
            f.unlink()
    edges_dir = WIKI_ROOT / "behavioral" / "_edges"
    for f in edges_dir.glob("*.md"):
        f.unlink()
    for sdir in (WIKI_ROOT / "students").iterdir():
        if sdir.is_dir():
            for f in sdir.rglob("*.md"):
                f.unlink()
            inc_dir = sdir / "incidents"
            if inc_dir.exists():
                shutil.rmtree(inc_dir)
    for f in (WIKI_ROOT / "sources" / "openalex").glob("*.md"):
        f.unlink()

    # 3. Reset index/log to skeleton state
    import subprocess
    subprocess.run(
        ["git", "checkout", "--", "wiki/log.md", "wiki/index.md", "wiki/behavioral/_index.md"],
        cwd=str(WIKI_ROOT.parent), capture_output=True,
    )

    return {"status": "purged", "message": "All data tables truncated. Wiki generated content removed. Personas and skeleton preserved."}
