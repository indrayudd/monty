from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import json
import shutil
import subprocess

from .note_parser import ParsedNote


class GhostBuildError(RuntimeError):
    """Raised when Ghost Build is unavailable or a CLI call fails."""


@dataclass(frozen=True)
class GhostBuildState:
    database_id: str
    database_name: str


class GhostBuildDatabase:
    def __init__(self, database_name: str, state_path: Path) -> None:
        self.database_name = database_name
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: GhostBuildState | None = None

    def initialize(self) -> None:
        self._state = self._resolve_state()
        self._run_sql(
            """
            CREATE TABLE IF NOT EXISTS ingested_observations (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                body TEXT NOT NULL,
                UNIQUE (name, body)
            );
            """
        )

    def insert_note(self, note: ParsedNote) -> bool:
        result = self._run_sql(
            f"""
            INSERT INTO ingested_observations (name, body)
            VALUES ({self._sql_literal(note.name)}, {self._sql_literal(note.body)})
            ON CONFLICT (name, body) DO NOTHING
            RETURNING id;
            """
        )
        return bool(result.stdout.strip())

    def _resolve_state(self) -> GhostBuildState:
        if self._state is not None:
            return self._state

        env_database_id = os.environ.get("GHOST_BUILD_DATABASE_ID", "").strip()
        if env_database_id:
            state = GhostBuildState(database_id=env_database_id, database_name=self.database_name)
            self._state = state
            return state

        if not shutil.which("ghost"):
            raise GhostBuildError(
                "Ghost Build CLI is not installed. Install it with `curl -fsSL https://install.ghost.build | sh` "
                "and run `ghost login` first."
            )

        if self.state_path.exists():
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                state = GhostBuildState(
                    database_id=payload["database_id"],
                    database_name=payload.get("database_name", self.database_name),
                )
                self._state = state
                return state
            except Exception as exc:  # pragma: no cover - defensive parse guard
                raise GhostBuildError(f"Failed to read Ghost Build state file: {self.state_path}") from exc

        created = self._run_ghost(
            "create",
            "--name",
            self.database_name,
            "--wait",
            "--json",
        )
        database_id = self._extract_database_id(created.stdout)
        state = GhostBuildState(database_id=database_id, database_name=self.database_name)
        self.state_path.write_text(
            json.dumps(
                {
                    "database_id": state.database_id,
                    "database_name": state.database_name,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self._state = state
        return state

    def _run_sql(self, sql: str) -> subprocess.CompletedProcess[str]:
        state = self._resolve_state()
        return self._run_ghost("sql", state.database_id, input_text=sql)

    def _run_ghost(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["ghost", *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise GhostBuildError(
                "Ghost Build CLI command failed: "
                f"ghost {' '.join(args)}\n{completed.stderr.strip() or completed.stdout.strip()}"
            )
        return completed

    @staticmethod
    def _extract_database_id(stdout: str) -> str:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise GhostBuildError("Ghost Build create command did not return JSON.") from exc

        def walk(value: object) -> str | None:
            if isinstance(value, dict):
                for key in ("id", "database_id", "databaseId"):
                    candidate = value.get(key)
                    if isinstance(candidate, str) and candidate:
                        return candidate
                for candidate in value.values():
                    found = walk(candidate)
                    if found:
                        return found
            elif isinstance(value, list):
                for candidate in value:
                    found = walk(candidate)
                    if found:
                        return found
            return None

        found = walk(payload)
        if found:
            return found
        raise GhostBuildError("Could not determine Ghost Build database id from create output.")

    @staticmethod
    def _sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
