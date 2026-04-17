from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


_ENV_PATHS = [
    Path(__file__).resolve().parents[3] / ".env",
    Path(__file__).resolve().parents[3] / "contracts" / ".env",
]

for env_path in _ENV_PATHS:
    if not env_path.exists():
        continue
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, _, val = line.partition("=")
        if key.strip() and val.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()


DB_PATH = Path(__file__).resolve().parents[3] / "data" / "monty.db"


def _conn():
    """Return a sqlite3 connection. Creates DB + directory if missing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(zip(row.keys(), tuple(row)))


def _fetchall(cur) -> list[dict]:
    return [_row_to_dict(r) for r in cur.fetchall()]


def _fetchone(cur) -> dict | None:
    row = cur.fetchone()
    return _row_to_dict(row)


def _json_dumps(value: Any) -> str:
    return json.dumps(value or [])


def _json_loads(value: Any) -> Any:
    if value in (None, ""):
        return []
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def ensure_agent_tables() -> None:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                note_id INT NOT NULL,
                severity TEXT NOT NULL,
                profile_summary TEXT,
                behavioral_patterns TEXT,
                suggestions TEXT,
                snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_name, note_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                student_name TEXT PRIMARY KEY,
                current_severity TEXT,
                previous_severity TEXT,
                trend TEXT,
                assessment_count INT DEFAULT 0,
                latest_summary TEXT,
                latest_patterns TEXT,
                latest_suggestions TEXT,
                first_assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_literature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                search_query TEXT NOT NULL,
                openalex_id TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                publication_year INT,
                cited_by_count INT DEFAULT 0,
                abstract TEXT,
                landing_page_url TEXT,
                relevance_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_name, openalex_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                note_id INT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                recommended_actions_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_name, note_id, alert_type, title)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                note_id INT,
                action_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runtime_state (
                key TEXT PRIMARY KEY,
                value_text TEXT,
                god_mode_overrides TEXT DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS behavioral_nodes (
                slug TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                literature_refs INT DEFAULT 0,
                curiosity_score REAL DEFAULT 0,
                curiosity_factors TEXT,
                last_observed_at TIMESTAMP,
                last_research_fetched_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMP NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS behavioral_edges (
                src_slug TEXT NOT NULL,
                rel TEXT NOT NULL,
                dst_slug TEXT NOT NULL,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                first_observed_at TIMESTAMP,
                last_observed_at TIMESTAMP,
                file_path TEXT NOT NULL,
                PRIMARY KEY (src_slug, rel, dst_slug)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                note_id INT,
                severity TEXT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMP NOT NULL,
                behavioral_ref_slugs TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_student_incidents_student_name
                ON student_incidents (student_name)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles_index (
                student_name TEXT PRIMARY KEY,
                current_severity TEXT,
                trend TEXT,
                incident_count INT DEFAULT 0,
                patterns_summary TEXT,
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMP NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS curiosity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_slug TEXT NOT NULL,
                fired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                curiosity_score REAL,
                factors TEXT,
                triggered_research BOOLEAN,
                paper_count INT DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_notes_table() -> None:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                body TEXT NOT NULL,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name, body)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_literature_table() -> None:
    ensure_agent_tables()


def get_all_notes() -> list[dict]:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, body FROM ingested_observations ORDER BY id;")
        return _fetchall(cur)
    finally:
        conn.close()


def get_notes_after(after_id: int) -> list[dict]:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, body
            FROM ingested_observations
            WHERE id > ?
            ORDER BY id;
            """,
            (after_id,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def get_notes_for_student(student_name: str) -> list[dict]:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, body
            FROM ingested_observations
            WHERE name = ?
            ORDER BY id;
            """,
            (student_name,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def get_latest_note_id() -> int:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM ingested_observations;")
        row = _fetchone(cur)
        return int((row or {}).get("max_id") or 0)
    finally:
        conn.close()


def count_notes() -> int:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM ingested_observations;")
        row = _fetchone(cur)
        return int((row or {}).get("total") or 0)
    finally:
        conn.close()


def insert_ingested_note(name: str, body: str) -> dict | None:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ingested_observations (name, body)
            VALUES (?, ?)
            ON CONFLICT (name, body) DO NOTHING;
            """,
            (name, body),
        )
        conn.commit()
        if cur.lastrowid and cur.rowcount > 0:
            cur.execute(
                "SELECT id, name, body, inserted_at FROM ingested_observations WHERE id = ?;",
                (cur.lastrowid,),
            )
            return _fetchone(cur)
        return None
    finally:
        conn.close()


def insert_observation(name: str, body: str) -> int:
    """Insert an observation into ingested_observations and return its id."""
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingested_observations (name, body) VALUES (?, ?) "
            "ON CONFLICT (name, body) DO UPDATE SET body = EXCLUDED.body",
            (name, body),
        )
        conn.commit()
        row_id = cur.lastrowid
        if not row_id:
            cur.execute(
                "SELECT id FROM ingested_observations WHERE name = ? AND body = ?",
                (name, body),
            )
            r = _fetchone(cur)
            row_id = (r or {}).get("id", 0)
        return row_id
    finally:
        conn.close()


def get_recent_notes(limit: int = 25) -> list[dict]:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, body, inserted_at
            FROM ingested_observations
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def insert_snapshot(snapshot: dict) -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO profile_snapshots (student_name, note_id, severity, profile_summary, behavioral_patterns, suggestions)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (student_name, note_id) DO UPDATE SET
                severity = EXCLUDED.severity,
                profile_summary = EXCLUDED.profile_summary,
                behavioral_patterns = EXCLUDED.behavioral_patterns,
                suggestions = EXCLUDED.suggestions,
                snapshot_at = CURRENT_TIMESTAMP;
            """,
            (
                snapshot["student_name"],
                snapshot["note_id"],
                snapshot["severity"],
                snapshot["profile_summary"],
                snapshot["behavioral_patterns"],
                snapshot["suggestions"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _sev_rank(severity: str | None) -> int:
    return {"green": 0, "yellow": 1, "red": 2}.get((severity or "").lower(), 1)


def upsert_student_profile(student_name: str, snapshot: dict, prev_severity: str | None, count: int) -> None:
    severity = snapshot["severity"]

    if prev_severity is None:
        trend = "stable"
    elif _sev_rank(severity) < _sev_rank(prev_severity):
        trend = "improving"
    elif _sev_rank(severity) > _sev_rank(prev_severity):
        trend = "declining"
    else:
        trend = "stable"

    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_profiles (
                student_name,
                current_severity,
                previous_severity,
                trend,
                assessment_count,
                latest_summary,
                latest_patterns,
                latest_suggestions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (student_name) DO UPDATE SET
                previous_severity = student_profiles.current_severity,
                current_severity = EXCLUDED.current_severity,
                trend = EXCLUDED.trend,
                assessment_count = EXCLUDED.assessment_count,
                latest_summary = EXCLUDED.latest_summary,
                latest_patterns = EXCLUDED.latest_patterns,
                latest_suggestions = EXCLUDED.latest_suggestions,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (
                student_name,
                severity,
                prev_severity,
                trend,
                count,
                snapshot["profile_summary"],
                snapshot["behavioral_patterns"],
                snapshot["suggestions"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_student_profile_state(student_name: str, aggregate: dict, assessment_count: int) -> dict:
    ensure_agent_tables()
    current = get_student_profile(student_name)
    previous_severity = current["current_severity"] if current else None
    severity = aggregate.get("severity") or "yellow"

    if previous_severity is None:
        trend = "stable"
    elif _sev_rank(severity) < _sev_rank(previous_severity):
        trend = "improving"
    elif _sev_rank(severity) > _sev_rank(previous_severity):
        trend = "declining"
    else:
        trend = "stable"

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_profiles (
                student_name,
                current_severity,
                previous_severity,
                trend,
                assessment_count,
                latest_summary,
                latest_patterns,
                latest_suggestions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (student_name) DO UPDATE SET
                previous_severity = student_profiles.current_severity,
                current_severity = EXCLUDED.current_severity,
                trend = EXCLUDED.trend,
                assessment_count = EXCLUDED.assessment_count,
                latest_summary = EXCLUDED.latest_summary,
                latest_patterns = EXCLUDED.latest_patterns,
                latest_suggestions = EXCLUDED.latest_suggestions,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (
                student_name,
                severity,
                previous_severity,
                trend,
                assessment_count,
                aggregate.get("profile_summary"),
                aggregate.get("behavioral_patterns"),
                aggregate.get("suggestions"),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {"student_name": student_name, "current_severity": severity, "previous_severity": previous_severity, "trend": trend}


def get_all_profiles() -> list[dict]:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT student_name, current_severity, previous_severity, trend,
                   assessment_count, latest_summary, latest_patterns, latest_suggestions, updated_at
            FROM student_profiles
            ORDER BY
                CASE current_severity WHEN 'red' THEN 0 WHEN 'yellow' THEN 1 ELSE 2 END,
                student_name;
            """
        )
        return _fetchall(cur)
    finally:
        conn.close()


def get_student_profile(student_name: str) -> dict | None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT student_name, current_severity, previous_severity, trend,
                   assessment_count, latest_summary, latest_patterns, latest_suggestions,
                   first_assessed_at, updated_at
            FROM student_profiles
            WHERE student_name = ?;
            """,
            (student_name,),
        )
        return _fetchone(cur)
    finally:
        conn.close()


def get_student_snapshots(student_name: str) -> list[dict]:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, note_id, snapshot_at, severity, profile_summary, behavioral_patterns, suggestions
            FROM profile_snapshots
            WHERE student_name = ?
            ORDER BY note_id;
            """,
            (student_name,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def replace_personality_graph(student_name: str, facets: list[dict]) -> None:
    # Legacy function — student_personality_graph table no longer exists.
    # Keep as no-op to avoid breaking callers.
    pass


def get_personality_graph(student_name: str) -> list[dict]:
    # Legacy function — student_personality_graph table no longer exists.
    return []


def insert_literature(row: dict) -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_literature
                (student_name, search_query, openalex_id, title, authors,
                 publication_year, cited_by_count, abstract, landing_page_url, relevance_summary)
            VALUES
                (?, ?, ?, ?, ?,
                 ?, ?, ?, ?, ?)
            ON CONFLICT (student_name, openalex_id) DO UPDATE SET
                relevance_summary = EXCLUDED.relevance_summary,
                search_query = EXCLUDED.search_query,
                created_at = CURRENT_TIMESTAMP;
            """,
            (
                row.get("student_name"),
                row.get("search_query"),
                row.get("openalex_id"),
                row.get("title"),
                row.get("authors"),
                row.get("publication_year"),
                row.get("cited_by_count"),
                row.get("abstract"),
                row.get("landing_page_url"),
                row.get("relevance_summary"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_student_literature(student_name: str) -> list[dict]:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT openalex_id, title, authors, publication_year, cited_by_count,
                   abstract, landing_page_url, search_query, relevance_summary, created_at
            FROM student_literature
            WHERE student_name = ?
            ORDER BY cited_by_count DESC, publication_year DESC;
            """,
            (student_name,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def upsert_knowledge_graph_entry(entry: dict) -> None:
    # Legacy function — knowledge_graph table no longer exists.
    # Keep as no-op to avoid breaking callers.
    pass


def get_knowledge_graph_entries(student_name: str | None = None, query: str | None = None, limit: int = 10) -> list[dict]:
    # Legacy function — knowledge_graph table no longer exists.
    return []


def insert_alert(alert: dict) -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO student_alerts (
                student_name, note_id, alert_type, severity, title, body, recommended_actions_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, 'open'))
            ON CONFLICT (student_name, note_id, alert_type, title) DO UPDATE SET
                severity = EXCLUDED.severity,
                body = EXCLUDED.body,
                recommended_actions_json = EXCLUDED.recommended_actions_json,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (
                alert.get("student_name"),
                alert.get("note_id"),
                alert.get("alert_type"),
                alert.get("severity"),
                alert.get("title"),
                alert.get("body"),
                _json_dumps(alert.get("recommended_actions")),
                alert.get("status"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_alerts(student_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    ensure_agent_tables()
    where_parts: list[str] = []
    params: list[Any] = []

    if student_name:
        where_parts.append("student_name = ?")
        params.append(student_name)
    if status:
        where_parts.append("status = ?")
        params.append(status)

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params.append(limit)

    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, student_name, note_id, alert_type, severity, title, body, recommended_actions_json,
                   status, created_at, updated_at
            FROM student_alerts
            {where_sql}
            ORDER BY
                CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                updated_at DESC
            LIMIT ?;
            """,
            tuple(params),
        )
        rows = _fetchall(cur)
    finally:
        conn.close()

    for row in rows:
        row["recommended_actions"] = _json_loads(row.pop("recommended_actions_json"))
    return rows


def insert_agent_action(action: dict) -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_actions (student_name, note_id, action_kind, status, payload_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                action.get("student_name"),
                action.get("note_id"),
                action.get("action_kind"),
                action.get("status"),
                _json_dumps(action.get("payload")),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_agent_actions(limit: int = 50) -> list[dict]:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, student_name, note_id, action_kind, status, payload_json, created_at
            FROM agent_actions
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = _fetchall(cur)
    finally:
        conn.close()
    for row in rows:
        row["payload"] = _json_loads(row.pop("payload_json"))
    return rows


def get_runtime_value(key: str, default: str | None = None) -> str | None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value_text FROM agent_runtime_state WHERE key = ?;", (key,))
        row = _fetchone(cur)
        if not row:
            return default
        return row.get("value_text") or default
    finally:
        conn.close()


def set_runtime_value(key: str, value: Any) -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_runtime_state (key, value_text)
            VALUES (?, ?)
            ON CONFLICT (key) DO UPDATE SET
                value_text = EXCLUDED.value_text,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


def set_runtime_values(values: dict[str, Any]) -> None:
    if not values:
        return
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        for key, value in values.items():
            cur.execute(
                """
                INSERT INTO agent_runtime_state (key, value_text)
                VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value_text = EXCLUDED.value_text,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (key, "" if value is None else str(value)),
            )
        conn.commit()
    finally:
        conn.close()


def delete_runtime_keys(keys: list[str]) -> None:
    if not keys:
        return
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in keys)
        cur.execute(f"DELETE FROM agent_runtime_state WHERE key IN ({placeholders});", keys)
        conn.commit()
    finally:
        conn.close()


def get_runtime_state() -> dict[str, str]:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value_text FROM agent_runtime_state ORDER BY key;")
        rows = _fetchall(cur)
    finally:
        conn.close()
    return {row["key"]: row.get("value_text") for row in rows}


def reset_notes_state() -> None:
    ensure_notes_table()
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM ingested_observations;")
        conn.commit()
    finally:
        conn.close()


def reset_agent_state() -> None:
    ensure_agent_tables()
    conn = _conn()
    try:
        cur = conn.cursor()
        for table in [
            "profile_snapshots",
            "student_literature",
            "student_alerts",
            "agent_actions",
            "student_profiles",
            "agent_runtime_state",
            "behavioral_nodes",
            "behavioral_edges",
            "student_incidents",
            "student_profiles_index",
            "curiosity_events",
        ]:
            cur.execute(f"DELETE FROM {table};")
        conn.commit()
    finally:
        conn.close()


def list_behavioral_nodes() -> list[dict]:
    """Return all rows from behavioral_nodes index. Empty list if none."""
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT slug, type, title, summary, support_count, students_count, "
            "literature_refs, curiosity_score, curiosity_factors, "
            "last_observed_at, last_research_fetched_at, created_at, file_path "
            "FROM behavioral_nodes ORDER BY support_count DESC"
        )
        rows = _fetchall(cur)
    finally:
        conn.close()
    for row in rows:
        row["curiosity_factors"] = _json_loads(row.get("curiosity_factors"))
    return rows


def list_behavioral_edges(min_support: int = 1) -> list[dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT src_slug, rel, dst_slug, support_count, students_count, "
            "first_observed_at, last_observed_at "
            "FROM behavioral_edges WHERE support_count >= ?",
            (min_support,),
        )
        return _fetchall(cur)
    finally:
        conn.close()


def list_student_incidents(student_name: str, limit: int = 50) -> list[dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, student_name, note_id, severity, ingested_at, file_path, "
            "behavioral_ref_slugs "
            "FROM student_incidents WHERE student_name = ? "
            "ORDER BY ingested_at DESC LIMIT ?",
            (student_name, limit),
        )
        rows = _fetchall(cur)
    finally:
        conn.close()
    for row in rows:
        row["behavioral_ref_slugs"] = _json_loads(row.get("behavioral_ref_slugs"))
    return rows


def list_curiosity_events(limit: int = 50) -> list[dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, node_slug, fired_at, curiosity_score, factors, "
            "triggered_research, paper_count "
            "FROM curiosity_events ORDER BY fired_at DESC LIMIT ?",
            (limit,),
        )
        rows = _fetchall(cur)
    finally:
        conn.close()
    for row in rows:
        row["factors"] = _json_loads(row.get("factors"))
    return rows


def get_runtime_overrides() -> dict:
    """Return agent_runtime_state.god_mode_overrides as a dict (empty if null)."""
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT god_mode_overrides FROM agent_runtime_state "
            "WHERE key = '_god_mode' LIMIT 1"
        )
        row = _fetchone(cur)
        if not row:
            return {}
        val = row.get("god_mode_overrides")
        if val is None:
            return {}
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return {}
        return val if val else {}
    finally:
        conn.close()


def set_runtime_overrides(overrides: dict) -> None:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_runtime_state (key, god_mode_overrides)
            VALUES ('_god_mode', ?)
            ON CONFLICT (key) DO UPDATE SET
                god_mode_overrides = EXCLUDED.god_mode_overrides,
                updated_at = CURRENT_TIMESTAMP
            """,
            (json.dumps(overrides),),
        )
        conn.commit()
    finally:
        conn.close()
