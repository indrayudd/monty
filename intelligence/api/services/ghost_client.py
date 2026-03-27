from __future__ import annotations

import psycopg2

DB1_URL = "postgresql://tsdbadmin:hfkcgdldf7nylyrv@e3ho885uvg.hb4jlylyua.tsdb.cloud.timescale.com:31313/tsdb"
DB2_URL = "postgresql://tsdbadmin:va4fd9zgfrleecd3@oman6716dt.hb4jlylyua.tsdb.cloud.timescale.com:39127/tsdb"


def _conn(url: str):
    return psycopg2.connect(url)


def get_all_notes() -> list[dict]:
    """Return all notes ordered by id (simulates chronological order)."""
    with _conn(DB1_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, body FROM ingested_observations ORDER BY id;")
        return [{"id": row[0], "name": row[1], "body": row[2]} for row in cur.fetchall()]


def insert_snapshot(snapshot: dict) -> None:
    with _conn(DB2_URL) as conn, conn.cursor() as cur:
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

    with _conn(DB2_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student_profiles (student_name, current_severity, previous_severity, trend, assessment_count, latest_summary, latest_patterns, latest_suggestions)
            VALUES (%(name)s, %(severity)s, %(prev)s, %(trend)s, %(count)s, %(summary)s, %(patterns)s, %(suggestions)s)
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
                "name": student_name,
                "severity": severity,
                "prev": prev_severity,
                "trend": trend,
                "count": count,
                "summary": snapshot["profile_summary"],
                "patterns": snapshot["behavioral_patterns"],
                "suggestions": snapshot["suggestions"],
            },
        )
        conn.commit()


def get_all_profiles() -> list[dict]:
    """All students sorted by severity (red first)."""
    with _conn(DB2_URL) as conn, conn.cursor() as cur:
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
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_student_profile(student_name: str) -> dict | None:
    with _conn(DB2_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT student_name, current_severity, previous_severity, trend,
                   assessment_count, latest_summary, latest_patterns, latest_suggestions,
                   first_assessed_at, updated_at
            FROM student_profiles WHERE student_name = %s;
            """,
            (student_name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def get_student_snapshots(student_name: str) -> list[dict]:
    with _conn(DB2_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, note_id, snapshot_at, severity, profile_summary, behavioral_patterns, suggestions
            FROM profile_snapshots
            WHERE student_name = %s
            ORDER BY note_id;
            """,
            (student_name,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _sev_rank(s: str) -> int:
    return {"green": 0, "yellow": 1, "red": 2}.get(s, 1)
