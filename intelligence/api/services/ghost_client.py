from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


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


DEFAULT_DB1_URL = "postgresql://tsdbadmin:cu3icrvyogvuibej@wwdclkvwu7.m5ptmvrzi0.tsdb.cloud.timescale.com:31109/tsdb"
DEFAULT_DB2_URL = "postgresql://tsdbadmin:c7hrt7hy360h947u@h55j4jft23.m5ptmvrzi0.tsdb.cloud.timescale.com:38711/tsdb"


def _notes_db_url() -> str:
    return (
        os.environ.get("MONTY_NOTES_DB_URL")
        or os.environ.get("GHOST_NOTES_DB_URL")
        or DEFAULT_DB1_URL
    )


def _agent_db_url() -> str:
    return (
        os.environ.get("MONTY_AGENT_DB_URL")
        or os.environ.get("GHOST_AGENT_DB_URL")
        or DEFAULT_DB2_URL
    )


def _conn(url: str):
    return psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=5)


def _fetchall(cur) -> list[dict]:
    return [dict(row) for row in cur.fetchall()]


def _fetchone(cur) -> dict | None:
    row = cur.fetchone()
    return dict(row) if row else None


def _json_dumps(value: Any) -> str:
    return json.dumps(value or [])


def _json_loads(value: Any) -> Any:
    if value in (None, ""):
        return []
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def ensure_agent_tables() -> None:
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_snapshots (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                note_id INT NOT NULL,
                severity TEXT NOT NULL,
                profile_summary TEXT,
                behavioral_patterns TEXT,
                suggestions TEXT,
                snapshot_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (student_name, note_id)
            );

            CREATE TABLE IF NOT EXISTS student_profiles (
                student_name TEXT PRIMARY KEY,
                current_severity TEXT,
                previous_severity TEXT,
                trend TEXT,
                assessment_count INT DEFAULT 0,
                latest_summary TEXT,
                latest_patterns TEXT,
                latest_suggestions TEXT,
                first_assessed_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS student_literature (
                id BIGSERIAL PRIMARY KEY,
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
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (student_name, openalex_id)
            );

            CREATE TABLE IF NOT EXISTS student_personality_graph (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                facet_type TEXT NOT NULL,
                facet_value TEXT NOT NULL,
                evidence TEXT,
                confidence DOUBLE PRECISION DEFAULT 0.5,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (student_name, facet_type, facet_value)
            );

            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT,
                topic TEXT NOT NULL,
                search_query TEXT,
                source_title TEXT,
                source_url TEXT NOT NULL,
                insights_json TEXT NOT NULL,
                related_topics_json TEXT NOT NULL,
                confidence DOUBLE PRECISION DEFAULT 0.5,
                evidence_summary TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (student_name, source_url, topic)
            );

            CREATE TABLE IF NOT EXISTS student_alerts (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                note_id INT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                recommended_actions_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (student_name, note_id, alert_type, title)
            );

            CREATE TABLE IF NOT EXISTS agent_actions (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT,
                note_id INT,
                action_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS agent_runtime_state (
                key TEXT PRIMARY KEY,
                value_text TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS behavioral_nodes (
                slug TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                literature_refs INT DEFAULT 0,
                curiosity_score REAL DEFAULT 0,
                curiosity_factors JSONB,
                last_observed_at TIMESTAMPTZ,
                last_research_fetched_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL
            );

            CREATE TABLE IF NOT EXISTS behavioral_edges (
                src_slug TEXT NOT NULL,
                rel TEXT NOT NULL,
                dst_slug TEXT NOT NULL,
                support_count INT DEFAULT 0,
                students_count INT DEFAULT 0,
                first_observed_at TIMESTAMPTZ,
                last_observed_at TIMESTAMPTZ,
                file_path TEXT NOT NULL,
                PRIMARY KEY (src_slug, rel, dst_slug)
            );

            CREATE TABLE IF NOT EXISTS student_incidents (
                id BIGSERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                note_id INT,
                severity TEXT,
                ingested_at TIMESTAMPTZ DEFAULT NOW(),
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL,
                behavioral_ref_slugs TEXT[]
            );

            CREATE INDEX IF NOT EXISTS idx_student_incidents_student_name
                ON student_incidents (student_name);

            CREATE INDEX IF NOT EXISTS idx_student_incidents_bref_slugs
                ON student_incidents USING GIN (behavioral_ref_slugs);

            CREATE TABLE IF NOT EXISTS student_profiles_index (
                student_name TEXT PRIMARY KEY,
                current_severity TEXT,
                trend TEXT,
                incident_count INT DEFAULT 0,
                patterns_summary TEXT,
                file_path TEXT NOT NULL,
                file_mtime TIMESTAMPTZ NOT NULL
            );

            CREATE TABLE IF NOT EXISTS curiosity_events (
                id BIGSERIAL PRIMARY KEY,
                node_slug TEXT NOT NULL,
                fired_at TIMESTAMPTZ DEFAULT NOW(),
                curiosity_score REAL,
                factors JSONB,
                triggered_research BOOLEAN,
                paper_count INT DEFAULT 0
            );

            ALTER TABLE agent_runtime_state
                ADD COLUMN IF NOT EXISTS god_mode_overrides JSONB DEFAULT '{}'::jsonb;
            """
        )
        conn.commit()


def ensure_notes_table() -> None:
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_observations (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                body TEXT NOT NULL,
                inserted_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (name, body)
            );

            ALTER TABLE ingested_observations
            ADD COLUMN IF NOT EXISTS inserted_at TIMESTAMPTZ DEFAULT NOW();
            """
        )
        conn.commit()


def ensure_literature_table() -> None:
    ensure_agent_tables()


def get_all_notes() -> list[dict]:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, body FROM ingested_observations ORDER BY id;")
        return _fetchall(cur)


def get_notes_after(after_id: int) -> list[dict]:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, body
            FROM ingested_observations
            WHERE id > %s
            ORDER BY id;
            """,
            (after_id,),
        )
        return _fetchall(cur)


def get_notes_for_student(student_name: str) -> list[dict]:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, body
            FROM ingested_observations
            WHERE name = %s
            ORDER BY id;
            """,
            (student_name,),
        )
        return _fetchall(cur)


def get_latest_note_id() -> int:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM ingested_observations;")
        row = _fetchone(cur)
        return int((row or {}).get("max_id") or 0)


def count_notes() -> int:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM ingested_observations;")
        row = _fetchone(cur)
        return int((row or {}).get("total") or 0)


def insert_ingested_note(name: str, body: str) -> dict | None:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingested_observations (name, body)
            VALUES (%s, %s)
            ON CONFLICT (name, body) DO NOTHING
            RETURNING id, name, body, inserted_at;
            """,
            (name, body),
        )
        row = _fetchone(cur)
        conn.commit()
        return row


def get_recent_notes(limit: int = 25) -> list[dict]:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, body, inserted_at
            FROM ingested_observations
            ORDER BY id DESC
            LIMIT %s;
            """,
            (limit,),
        )
        return _fetchall(cur)


def insert_snapshot(snapshot: dict) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO profile_snapshots (student_name, note_id, severity, profile_summary, behavioral_patterns, suggestions)
            VALUES (%(student_name)s, %(note_id)s, %(severity)s, %(profile_summary)s, %(behavioral_patterns)s, %(suggestions)s)
            ON CONFLICT (student_name, note_id) DO UPDATE SET
                severity = EXCLUDED.severity,
                profile_summary = EXCLUDED.profile_summary,
                behavioral_patterns = EXCLUDED.behavioral_patterns,
                suggestions = EXCLUDED.suggestions,
                snapshot_at = NOW();
            """,
            snapshot,
        )
        conn.commit()


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
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
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
            VALUES (%(student_name)s, %(severity)s, %(previous_severity)s, %(trend)s, %(assessment_count)s,
                    %(latest_summary)s, %(latest_patterns)s, %(latest_suggestions)s)
            ON CONFLICT (student_name) DO UPDATE SET
                previous_severity = student_profiles.current_severity,
                current_severity = EXCLUDED.current_severity,
                trend = EXCLUDED.trend,
                assessment_count = EXCLUDED.assessment_count,
                latest_summary = EXCLUDED.latest_summary,
                latest_patterns = EXCLUDED.latest_patterns,
                latest_suggestions = EXCLUDED.latest_suggestions,
                updated_at = NOW();
            """,
            {
                "student_name": student_name,
                "severity": severity,
                "previous_severity": prev_severity,
                "trend": trend,
                "assessment_count": count,
                "latest_summary": snapshot["profile_summary"],
                "latest_patterns": snapshot["behavioral_patterns"],
                "latest_suggestions": snapshot["suggestions"],
            },
        )
        conn.commit()


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

    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_name) DO UPDATE SET
                previous_severity = student_profiles.current_severity,
                current_severity = EXCLUDED.current_severity,
                trend = EXCLUDED.trend,
                assessment_count = EXCLUDED.assessment_count,
                latest_summary = EXCLUDED.latest_summary,
                latest_patterns = EXCLUDED.latest_patterns,
                latest_suggestions = EXCLUDED.latest_suggestions,
                updated_at = NOW();
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
    return {"student_name": student_name, "current_severity": severity, "previous_severity": previous_severity, "trend": trend}


def get_all_profiles() -> list[dict]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
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


def get_student_profile(student_name: str) -> dict | None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT student_name, current_severity, previous_severity, trend,
                   assessment_count, latest_summary, latest_patterns, latest_suggestions,
                   first_assessed_at, updated_at
            FROM student_profiles
            WHERE student_name = %s;
            """,
            (student_name,),
        )
        return _fetchone(cur)


def get_student_snapshots(student_name: str) -> list[dict]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, note_id, snapshot_at, severity, profile_summary, behavioral_patterns, suggestions
            FROM profile_snapshots
            WHERE student_name = %s
            ORDER BY note_id;
            """,
            (student_name,),
        )
        return _fetchall(cur)


def replace_personality_graph(student_name: str, facets: list[dict]) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM student_personality_graph WHERE student_name = %s;", (student_name,))
        for facet in facets:
            cur.execute(
                """
                INSERT INTO student_personality_graph (
                    student_name, facet_type, facet_value, evidence, confidence
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    student_name,
                    facet.get("facet_type"),
                    facet.get("facet_value"),
                    facet.get("evidence"),
                    float(facet.get("confidence") or 0.5),
                ),
            )
        conn.commit()


def get_personality_graph(student_name: str) -> list[dict]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT facet_type, facet_value, evidence, confidence, updated_at
            FROM student_personality_graph
            WHERE student_name = %s
            ORDER BY facet_type, confidence DESC, facet_value;
            """,
            (student_name,),
        )
        return _fetchall(cur)


def insert_literature(row: dict) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student_literature
                (student_name, search_query, openalex_id, title, authors,
                 publication_year, cited_by_count, abstract, landing_page_url, relevance_summary)
            VALUES
                (%(student_name)s, %(search_query)s, %(openalex_id)s, %(title)s, %(authors)s,
                 %(publication_year)s, %(cited_by_count)s, %(abstract)s, %(landing_page_url)s, %(relevance_summary)s)
            ON CONFLICT (student_name, openalex_id) DO UPDATE SET
                relevance_summary = EXCLUDED.relevance_summary,
                search_query = EXCLUDED.search_query,
                created_at = NOW();
            """,
            row,
        )
        conn.commit()


def get_student_literature(student_name: str) -> list[dict]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT openalex_id, title, authors, publication_year, cited_by_count,
                   abstract, landing_page_url, search_query, relevance_summary, created_at
            FROM student_literature
            WHERE student_name = %s
            ORDER BY cited_by_count DESC, publication_year DESC NULLS LAST;
            """,
            (student_name,),
        )
        return _fetchall(cur)


def upsert_knowledge_graph_entry(entry: dict) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_graph (
                student_name, topic, search_query, source_title, source_url,
                insights_json, related_topics_json, confidence, evidence_summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_name, source_url, topic) DO UPDATE SET
                search_query = EXCLUDED.search_query,
                source_title = EXCLUDED.source_title,
                insights_json = EXCLUDED.insights_json,
                related_topics_json = EXCLUDED.related_topics_json,
                confidence = EXCLUDED.confidence,
                evidence_summary = EXCLUDED.evidence_summary,
                updated_at = NOW();
            """,
            (
                entry.get("student_name"),
                entry.get("topic"),
                entry.get("search_query"),
                entry.get("source_title"),
                entry.get("source_url"),
                _json_dumps(entry.get("insights")),
                _json_dumps(entry.get("related_topics")),
                float(entry.get("confidence") or 0.5),
                entry.get("evidence_summary"),
            ),
        )
        conn.commit()


def get_knowledge_graph_entries(student_name: str | None = None, query: str | None = None, limit: int = 10) -> list[dict]:
    ensure_agent_tables()
    where_parts: list[str] = []
    params: list[Any] = []

    if student_name:
        where_parts.append("(student_name = %s OR student_name IS NULL)")
        params.append(student_name)

    if query:
        like = f"%{query}%"
        where_parts.append(
            "(topic ILIKE %s OR COALESCE(search_query, '') ILIKE %s OR COALESCE(source_title, '') ILIKE %s OR COALESCE(evidence_summary, '') ILIKE %s OR insights_json ILIKE %s)"
        )
        params.extend([like, like, like, like, like])

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params.append(limit)

    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, student_name, topic, search_query, source_title, source_url,
                   insights_json, related_topics_json, confidence, evidence_summary, created_at, updated_at
            FROM knowledge_graph
            {where_sql}
            ORDER BY confidence DESC, updated_at DESC
            LIMIT %s;
            """,
            tuple(params),
        )
        rows = _fetchall(cur)

    for row in rows:
        row["insights"] = _json_loads(row.pop("insights_json"))
        row["related_topics"] = _json_loads(row.pop("related_topics_json"))
    return rows


def insert_alert(alert: dict) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student_alerts (
                student_name, note_id, alert_type, severity, title, body, recommended_actions_json, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, 'open'))
            ON CONFLICT (student_name, note_id, alert_type, title) DO UPDATE SET
                severity = EXCLUDED.severity,
                body = EXCLUDED.body,
                recommended_actions_json = EXCLUDED.recommended_actions_json,
                status = EXCLUDED.status,
                updated_at = NOW();
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


def get_alerts(student_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    ensure_agent_tables()
    where_parts: list[str] = []
    params: list[Any] = []

    if student_name:
        where_parts.append("student_name = %s")
        params.append(student_name)
    if status:
        where_parts.append("status = %s")
        params.append(status)

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params.append(limit)

    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, student_name, note_id, alert_type, severity, title, body, recommended_actions_json,
                   status, created_at, updated_at
            FROM student_alerts
            {where_sql}
            ORDER BY
                CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                updated_at DESC
            LIMIT %s;
            """,
            tuple(params),
        )
        rows = _fetchall(cur)

    for row in rows:
        row["recommended_actions"] = _json_loads(row.pop("recommended_actions_json"))
    return rows


def insert_agent_action(action: dict) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_actions (student_name, note_id, action_kind, status, payload_json)
            VALUES (%s, %s, %s, %s, %s);
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


def get_agent_actions(limit: int = 50) -> list[dict]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, student_name, note_id, action_kind, status, payload_json, created_at
            FROM agent_actions
            ORDER BY id DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = _fetchall(cur)
    for row in rows:
        row["payload"] = _json_loads(row.pop("payload_json"))
    return rows


def get_runtime_value(key: str, default: str | None = None) -> str | None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT value_text FROM agent_runtime_state WHERE key = %s;", (key,))
        row = _fetchone(cur)
        if not row:
            return default
        return row.get("value_text") or default


def set_runtime_value(key: str, value: Any) -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_runtime_state (key, value_text)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET
                value_text = EXCLUDED.value_text,
                updated_at = NOW();
            """,
            (key, str(value)),
        )
        conn.commit()


def set_runtime_values(values: dict[str, Any]) -> None:
    if not values:
        return
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        for key, value in values.items():
            cur.execute(
                """
                INSERT INTO agent_runtime_state (key, value_text)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value_text = EXCLUDED.value_text,
                    updated_at = NOW();
                """,
                (key, "" if value is None else str(value)),
            )
        conn.commit()


def delete_runtime_keys(keys: list[str]) -> None:
    if not keys:
        return
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM agent_runtime_state WHERE key = ANY(%s);", (keys,))
        conn.commit()


def get_runtime_state() -> dict[str, str]:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT key, value_text FROM agent_runtime_state ORDER BY key;")
        rows = _fetchall(cur)
    return {row["key"]: row.get("value_text") for row in rows}


def reset_notes_state() -> None:
    ensure_notes_table()
    with _conn(_notes_db_url()) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE ingested_observations RESTART IDENTITY;")
        conn.commit()


def reset_agent_state() -> None:
    ensure_agent_tables()
    with _conn(_agent_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            TRUNCATE profile_snapshots,
                     student_literature,
                     student_personality_graph,
                     knowledge_graph,
                     student_alerts,
                     agent_actions
            RESTART IDENTITY;

            TRUNCATE student_profiles;
            TRUNCATE agent_runtime_state;
            """
        )
        conn.commit()
