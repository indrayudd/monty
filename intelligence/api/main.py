from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from intelligence.api.services.ghost_client import (
    get_all_profiles,
    get_student_profile,
    get_student_snapshots,
)

app = FastAPI(title="PEP OS Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/flags")
def all_flags():
    """All students' current severity + trend, sorted red -> yellow -> green."""
    profiles = get_all_profiles()
    return {"students": profiles}


@app.get("/api/flags/{student_name}")
def student_flags(student_name: str):
    """One student's full snapshot history."""
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    snapshots = get_student_snapshots(student_name)
    return {"profile": profile, "snapshots": snapshots}


@app.get("/api/insights/{student_name}")
def student_insights(student_name: str):
    """Latest summary, behavioral patterns, and trend for a student."""
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
    """Latest suggestions for a student."""
    profile = get_student_profile(student_name)
    if not profile:
        raise HTTPException(404, f"Student '{student_name}' not found")
    return {
        "student_name": student_name,
        "severity": profile["current_severity"],
        "trend": profile["trend"],
        "suggestions": profile["latest_suggestions"],
    }
