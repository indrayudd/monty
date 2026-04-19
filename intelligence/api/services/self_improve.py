from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re

from intelligence.api.services.ghost_client import (
    get_alerts,
    get_all_profiles,
    get_notes_after,
    get_notes_for_student,
    get_runtime_value,
    insert_agent_action,
    insert_alert,
    insert_snapshot,
    set_runtime_value,
    set_runtime_values,
    upsert_student_profile_state,
)
from intelligence.api.services.kg_agent import enrich_student_knowledge
from intelligence.api.services.llm_service import assess_note, assess_student_history


EMERGENCY_RULES = {
    "killing threat": re.compile(r"\bkill(?:ing)?\b", re.IGNORECASE),
    "stabbing threat": re.compile(r"\bstab(?:bing)?\b", re.IGNORECASE),
    "shooting threat": re.compile(r"\bshoot(?:ing)?\b", re.IGNORECASE),
    "self-harm statement": re.compile(r"hurt (?:myself|himself|herself|themselves)", re.IGNORECASE),
    "weapon access": re.compile(r"\bweapon\b|\bscissors\b|\bpencil\b", re.IGNORECASE),
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def detect_emergency_terms(notes: list[dict]) -> list[str]:
    hits: list[str] = []
    for note in notes:
        body = note["body"]
        for label, pattern in EMERGENCY_RULES.items():
            if pattern.search(body):
                hits.append(label)
    deduped: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        if hit in seen:
            continue
        seen.add(hit)
        deduped.append(hit)
    return deduped


def _build_personality_facets(assessment: dict) -> list[dict]:
    facets: list[dict] = []
    mapping = {
        "personality_trait": assessment.get("personality_traits") or [],
        "regulation_trigger": assessment.get("regulation_triggers") or [],
        "support_strategy": assessment.get("support_strategies") or [],
        "behavioral_pattern": [part.strip() for part in str(assessment.get("behavioral_patterns") or "").split(",") if part.strip()],
    }
    evidence = assessment.get("profile_summary") or assessment.get("alert_reason") or ""
    for facet_type, values in mapping.items():
        for value in values:
            facets.append(
                {
                    "facet_type": facet_type,
                    "facet_value": value,
                    "evidence": evidence[:500],
                    "confidence": 0.7 if facet_type != "behavioral_pattern" else 0.8,
                }
            )
    return facets


def _alert_severity(assessment: dict, emergency_terms: list[str]) -> str:
    if emergency_terms or assessment.get("emergency_action_required"):
        return "critical"
    severity = (assessment.get("severity") or "yellow").lower()
    return {"red": "high", "yellow": "medium", "green": "low"}.get(severity, "medium")


def _recommended_actions(assessment: dict, knowledge_results: list[dict], emergency_terms: list[str]) -> list[str]:
    actions: list[str] = []
    actions.extend(assessment.get("support_strategies") or [])
    if emergency_terms:
        actions.insert(0, "Move immediately into the safety protocol, clear peers, and keep continuous adult supervision.")
    for node in knowledge_results[:2]:
        for insight in node.get("insights") or []:
            actions.append(insight)
    deduped: list[str] = []
    seen: set[str] = set()
    for action in actions:
        cleaned = str(action).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped[:5]


def _create_or_update_alert(student_name: str, latest_note_id: int, assessment: dict, emergency_terms: list[str], knowledge_results: list[dict]) -> dict:
    severity = _alert_severity(assessment, emergency_terms)
    if emergency_terms:
        alert_type = "emergency"
        title = f"Emergency escalation for {student_name}"
        body = (
            f"Detected high-risk language or actions: {', '.join(emergency_terms)}. "
            f"{assessment.get('alert_reason') or assessment.get('profile_summary')}"
        )
    else:
        alert_type = "profile_update"
        title = f"Profile update for {student_name}"
        body = assessment.get("alert_reason") or assessment.get("profile_summary") or "Profile updated from new note history."

    alert = {
        "student_name": student_name,
        "note_id": latest_note_id,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "body": body,
        "recommended_actions": _recommended_actions(assessment, knowledge_results, emergency_terms),
        "status": "open",
    }
    insert_alert(alert)
    return alert


def _log_action(student_name: str, note_id: int | None, action_kind: str, status: str, payload: dict) -> None:
    insert_agent_action(
        {
            "student_name": student_name,
            "note_id": note_id,
            "action_kind": action_kind,
            "status": status,
            "payload": payload,
        }
    )


def _set_stage(
    stage: str,
    *,
    student_name: str | None = None,
    note_id: int | None = None,
    message: str | None = None,
) -> None:
    set_runtime_values(
        {
            "current_stage": stage,
            "current_student": student_name,
            "current_note_id": note_id,
            "stage_started_at": _utcnow(),
            "stage_message": message or "",
        }
    )


def run_agent_cycle(force_full: bool = False, verbose: bool = True) -> dict:
    last_processed = 0 if force_full else int(get_runtime_value("last_processed_note_id", "0") or "0")
    new_notes = get_notes_after(last_processed)
    cycle_started_at = _utcnow()

    if verbose:
        print(
            f"[agent-cycle] cycle_started_at={cycle_started_at} "
            f"last_processed_note_id={last_processed} incoming_notes={len(new_notes)}",
            flush=True,
        )

    if not new_notes:
        _set_stage("waiting_for_note", message="Watching for the next classroom observation.")
        set_runtime_value("last_cycle_at", cycle_started_at)
        return {
            "cycle_started_at": cycle_started_at,
            "new_notes": 0,
            "students_processed": 0,
            "new_knowledge_nodes": 0,
            "alerts_open": len(get_alerts(status="open")),
        }

    impacted: dict[str, list[dict]] = defaultdict(list)
    for note in new_notes:
        impacted[note["name"]].append(note)

    total_knowledge_nodes = 0
    processed_students: list[dict] = []

    # Process at most MAX_NOTES_PER_CYCLE total across all students per cycle.
    # This keeps cycles short so the UI never looks stuck on one student.
    # Unprocessed notes stay in the queue and get picked up next cycle.
    MAX_NOTES_PER_CYCLE = 10

    # Interleave: take notes round-robin across students so no single student hogs the cycle
    student_queues: dict[str, list[dict]] = {}
    for student_name, notes_list in impacted.items():
        student_queues[student_name] = list(notes_list)  # copy

    cycle_notes: list[tuple[str, dict]] = []
    while len(cycle_notes) < MAX_NOTES_PER_CYCLE and any(student_queues.values()):
        for sname in list(student_queues.keys()):
            if len(cycle_notes) >= MAX_NOTES_PER_CYCLE:
                break
            if student_queues[sname]:
                cycle_notes.append((sname, student_queues[sname].pop(0)))
            if not student_queues[sname]:
                del student_queues[sname]

    # Regroup by student for processing
    cycle_impacted: dict[str, list[dict]] = defaultdict(list)
    for sname, note in cycle_notes:
        cycle_impacted[sname].append(note)

    if verbose and len(new_notes) > MAX_NOTES_PER_CYCLE:
        print(
            f"[agent-cycle] backlog={len(new_notes)}, processing {len(cycle_notes)} this cycle "
            f"({len(cycle_impacted)} students), remainder queued for next cycle",
            flush=True,
        )

    for student_name, student_new_notes in cycle_impacted.items():
        latest_note_id = max(note["id"] for note in student_new_notes)
        _set_stage(
            "reassessing_student",
            student_name=student_name,
            note_id=latest_note_id,
            message=f"Reassessing {student_name} from {len(student_new_notes)} new note(s).",
        )
        if verbose:
            note_ids = [note["id"] for note in student_new_notes]
            print(
                f"[agent-cycle] {student_name}: ingesting note_ids={note_ids}",
                flush=True,
            )
        all_ref_paths: list[str] = []
        total_notes_for_student = len(student_new_notes)
        for note_idx, note in enumerate(student_new_notes):
            set_runtime_values({
                "stage_progress": f"{note_idx + 1}/{total_notes_for_student}",
            })
            snapshot = assess_note(student_name, note["body"])
            snapshot["note_id"] = note["id"]
            insert_snapshot(snapshot)
            if verbose:
                print(
                    f"[agent-cycle][note] {student_name} note_id={note['id']} "
                    f"snapshot_severity={snapshot.get('severity')} "
                    f"text='{_preview(note['body'])}'",
                    flush=True,
                )

            # --- wiki_writer integration ---
            # Expects assessment dict to include 'behavioral_nodes': list of {type, slug, title, summary, evidence}
            # and 'behavioral_edges': list of {src_type, src_slug, rel, dst_type, dst_slug, evidence}.
            # If assess_note doesn't yet return these fields (pre-Task 2.7), these are no-ops.
            from intelligence.api.services import wiki_writer as _ww
            from intelligence.api.services.anonymization_lint import KNOWN_STUDENT_NAMES
            import re as _re

            def _scrub_names(text: str) -> str:
                """Best-effort: replace known student names (full and first-name) with neutral tokens.
                The anonymization lint is still the final authority — this just helps get past
                LLM outputs that leaked a name despite the prompt's instructions."""
                if not text:
                    return text
                for full_name in KNOWN_STUDENT_NAMES:
                    text = text.replace(full_name, "the child")
                    first = full_name.split()[0]
                    text = _re.sub(rf"\b{_re.escape(first)}\b", "the child", text)
                return text

            assessment_nodes = snapshot.get("behavioral_nodes") or []
            assessment_edges = snapshot.get("behavioral_edges") or []

            ref_paths: list[str] = []
            for n in assessment_nodes:
                try:
                    _ww.upsert_behavioral_node(
                        node_type=n["type"],
                        slug=n["slug"],
                        title=n.get("title", n["slug"].replace("-", " ").title()),
                        summary=_scrub_names(n.get("summary", "")),
                        new_evidence=_scrub_names(n["evidence"]),
                        new_student_name=student_name,
                    )
                    ref_paths.append(f"behavioral/{n['type']}/{n['slug']}")
                except Exception as _ne:
                    import sys as _sys
                    print(f"[self_improve] node upsert failed: {_ne}", file=_sys.stderr, flush=True)

            for _e in assessment_edges:
                try:
                    _ww.upsert_behavioral_edge(
                        src_type=_e["src_type"],
                        src_slug=_e["src_slug"],
                        rel=_e["rel"],
                        dst_type=_e["dst_type"],
                        dst_slug=_e["dst_slug"],
                        new_evidence=_scrub_names(_e["evidence"]),
                        new_student_name=student_name,
                    )
                except Exception as _ex:
                    import sys as _sys
                    print(f"[self_improve] edge upsert failed: {_ex}", file=_sys.stderr, flush=True)

            # Write the incident page itself.
            ingested_at = datetime.now(timezone.utc).isoformat()
            try:
                _ww.write_incident(
                    student_name=student_name,
                    note_id=note["id"],
                    severity=snapshot.get("severity", "yellow"),
                    note_body=note["body"],
                    interpretation=snapshot.get("profile_summary", ""),
                    behavioral_refs=ref_paths,
                    peers_present=snapshot.get("peers_present", []) or [],
                    educator=snapshot.get("educator", "") or "",
                    ingested_at_iso=ingested_at,
                    slug_hint=snapshot.get("slug_hint", f"note-{note['id']}"),
                )
                _ww.update_student_rollups(student_name)
                _ww.update_indexes()
                _ww.append_log(
                    "incident_written",
                    f"{student_name} note #{note['id']}",
                    student_name=student_name,
                )
            except Exception as _ex:
                import sys as _sys
                print(f"[self_improve] wiki write failed: {_ex}", file=_sys.stderr, flush=True)
            all_ref_paths.extend(ref_paths)
            # --- end wiki_writer integration ---

        all_student_notes = get_notes_for_student(student_name)
        aggregate = assess_student_history(student_name, all_student_notes)
        set_runtime_values({"stage_progress": "1/1"})  # single-step
        _set_stage(
            "updating_profile",
            student_name=student_name,
            note_id=latest_note_id,
            message=f"Updating cumulative profile for {student_name}.",
        )
        profile_state = upsert_student_profile_state(student_name, aggregate, assessment_count=len(all_student_notes))
        # replace_personality_graph removed in Phase 5b: student_personality_graph table was dropped.
        # Personality facets now live in wiki/students/<Name>/profile.md + patterns.md
        # (generated by wiki_writer.update_student_rollups above).

        if verbose:
            print(
                f"[agent-cycle][profile] {student_name}: total_notes={len(all_student_notes)} "
                f"severity={aggregate.get('severity')} trend={profile_state.get('trend')} "
                f"patterns={aggregate.get('behavioral_patterns')}",
                flush=True,
            )
            print(
                f"[agent-cycle][profile] {student_name}: summary='{_preview(aggregate.get('profile_summary') or '')}'",
                flush=True,
            )
            if aggregate.get("knowledge_gaps"):
                print(
                    f"[agent-cycle][profile] {student_name}: knowledge_gaps={aggregate.get('knowledge_gaps')}",
                    flush=True,
                )

        emergency_terms = detect_emergency_terms(student_new_notes)
        if verbose:
            print(
                f"[agent-cycle][knowledge] {student_name}: "
                f"emergency_terms={emergency_terms}",
                flush=True,
            )
        # Evaluate curiosity gate on all behavioral nodes from this student's
        # new notes. This populates curiosity_events for the /console stream,
        # and identifies nodes worth researching.
        from intelligence.api.services.curiosity import evaluate_gate as _eval_gate
        seen_refs: set[str] = set()
        fired_nodes: list[dict] = []
        for ref_path in all_ref_paths:
            slug_key = ref_path.replace("behavioral/", "")
            if slug_key in seen_refs:
                continue
            seen_refs.add(slug_key)
            try:
                gate_result = _eval_gate(slug_key)
                if gate_result.get("fire"):
                    # Extract type and slug from the key (e.g. "behaviors/calm-body")
                    parts = slug_key.split("/")
                    fired_nodes.append({
                        "type": parts[0] if len(parts) > 1 else "behaviors",
                        "slug": parts[-1],
                    })
            except Exception:
                pass

        if verbose and fired_nodes:
            print(
                f"[agent-cycle][curiosity] {student_name}: gate fired for "
                f"{[n['slug'] for n in fired_nodes]}",
                flush=True,
            )

        # Inject fired nodes into aggregate so enrich_student_knowledge
        # can find them via _curious_nodes_for_assessment
        aggregate["behavioral_nodes"] = fired_nodes

        knowledge_payload = {"results": [], "new_nodes_created": 0, "queries": []}
        if True:
            total_students = len(cycle_impacted)
            student_idx = list(cycle_impacted.keys()).index(student_name) + 1
            _set_stage(
                "enriching_knowledge",
                student_name=student_name,
                note_id=latest_note_id,
                message=f"Expanding research memory for {student_name} ({student_idx}/{total_students}).",
            )
            set_runtime_values({
                "enrich_progress": f"{student_idx}/{total_students}",
                "enrich_student": student_name,
                "stage_progress": f"{student_idx}/{total_students}",
                "enrich_query_progress": "",
            })
            knowledge_payload = enrich_student_knowledge(
                student_name,
                aggregate,
                emergency_terms=emergency_terms,
                verbose=verbose,
            )

        total_knowledge_nodes += int(knowledge_payload.get("new_nodes_created") or 0)
        knowledge_results = knowledge_payload.get("results") or []
        set_runtime_values({"stage_progress": "1/1"})
        _set_stage(
            "writing_alert",
            student_name=student_name,
            note_id=latest_note_id,
            message=f"Writing alert and recommendations for {student_name}.",
        )
        alert = _create_or_update_alert(student_name, latest_note_id, aggregate, emergency_terms, knowledge_results)

        _log_action(
            student_name=student_name,
            note_id=latest_note_id,
            action_kind="agent_cycle",
            status="success",
            payload={
                "severity": aggregate.get("severity"),
                "trend": profile_state.get("trend"),
                "emergency_terms": emergency_terms,
                "queries": knowledge_payload.get("queries") or [],
                "new_nodes_created": knowledge_payload.get("new_nodes_created") or 0,
                "alert_title": alert["title"],
            },
        )

        if verbose:
            print(
                f"[agent-cycle] {student_name}: severity={aggregate.get('severity')} "
                f"trend={profile_state.get('trend')} new_notes={len(student_new_notes)} "
                f"knowledge+={knowledge_payload.get('new_nodes_created') or 0}"
            )
            print(
                f"[agent-cycle][alert] {student_name}: {alert['severity']} {alert['title']}",
                flush=True,
            )
            print(
                f"[agent-cycle][alert] {student_name}: body='{_preview(alert['body'])}'",
                flush=True,
            )
            if emergency_terms:
                print(f"[agent-cycle][emergency] {student_name}: {', '.join(emergency_terms)}")
            for action in alert["recommended_actions"]:
                print(f"[agent-cycle][action] {student_name}: {action}", flush=True)

        processed_students.append(
            {
                "student_name": student_name,
                "new_notes": len(student_new_notes),
                "severity": aggregate.get("severity"),
                "trend": profile_state.get("trend"),
                "emergency_terms": emergency_terms,
                "new_knowledge_nodes": knowledge_payload.get("new_nodes_created") or 0,
                "alert": alert["title"],
            }
        )

    # Only advance checkpoint to what we actually processed this cycle
    processed_note_ids = [n["id"] for _, n in cycle_notes]
    set_runtime_value("last_processed_note_id", max(processed_note_ids))
    set_runtime_value("last_cycle_at", cycle_started_at)
    set_runtime_value("last_cycle_student_count", len(processed_students))
    remaining = len(new_notes) - len(cycle_notes)
    _set_stage(
        "cycle_complete",
        message=f"Processed {len(cycle_notes)} note(s) across {len(processed_students)} student(s)."
        + (f" {remaining} queued for next cycle." if remaining > 0 else ""),
    )
    # Clear stale progress values
    set_runtime_values({
        "stage_progress": "",
        "enrich_progress": "",
        "enrich_query_progress": "",
        "enrich_student": "",
    })

    return {
        "cycle_started_at": cycle_started_at,
        "new_notes": len(cycle_notes),
        "students_processed": len(processed_students),
        "new_knowledge_nodes": total_knowledge_nodes,
        "alerts_open": len(get_alerts(status="open")),
        "processed_students": processed_students,
        "profile_count": len(get_all_profiles()),
    }
