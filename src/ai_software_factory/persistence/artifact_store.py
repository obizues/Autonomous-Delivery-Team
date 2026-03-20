from __future__ import annotations

import pickle
import sqlite3
from pathlib import Path
from typing import Protocol

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.domain.enums import WorkflowStage


class ArtifactStore(Protocol):
    def save(self, artifact: BaseArtifact) -> None:
        ...

    def get(self, artifact_id: str) -> BaseArtifact | None:
        ...

    def list_by_workflow(self, workflow_id: str) -> list[BaseArtifact]:
        ...

    def list_by_stage(self, workflow_id: str, stage: WorkflowStage) -> list[BaseArtifact]:
        ...

class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, BaseArtifact] = {}
        self._by_workflow: dict[str, list[str]] = {}

    def save(self, artifact: BaseArtifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact
        self._by_workflow.setdefault(artifact.workflow_id, []).append(artifact.artifact_id)

    def get(self, artifact_id: str) -> BaseArtifact | None:
        return self._artifacts.get(artifact_id)

    def list_by_workflow(self, workflow_id: str) -> list[BaseArtifact]:
        artifact_ids = self._by_workflow.get(workflow_id, [])
        return [self._artifacts[artifact_id] for artifact_id in artifact_ids]

    def list_by_stage(self, workflow_id: str, stage: WorkflowStage) -> list[BaseArtifact]:
        return [artifact for artifact in self.list_by_workflow(workflow_id) if artifact.stage == stage]


class SQLiteArtifactStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id TEXT NOT NULL UNIQUE,
                workflow_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                payload BLOB NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_workflow_id ON artifacts(workflow_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_workflow_stage ON artifacts(workflow_id, stage)"
        )
        self._conn.commit()

    def save(self, artifact: BaseArtifact) -> None:
        payload = sqlite3.Binary(pickle.dumps(artifact, protocol=pickle.HIGHEST_PROTOCOL))
        self._conn.execute(
            """
            INSERT INTO artifacts (artifact_id, workflow_id, stage, artifact_type, payload)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                workflow_id=excluded.workflow_id,
                stage=excluded.stage,
                artifact_type=excluded.artifact_type,
                payload=excluded.payload
            """,
            (
                artifact.artifact_id,
                artifact.workflow_id,
                artifact.stage.value,
                artifact.__class__.__name__,
                payload,
            ),
        )
        self._conn.commit()

    def get(self, artifact_id: str) -> BaseArtifact | None:
        row = self._conn.execute(
            "SELECT payload FROM artifacts WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def list_by_workflow(self, workflow_id: str) -> list[BaseArtifact]:
        rows = self._conn.execute(
            "SELECT payload FROM artifacts WHERE workflow_id = ? ORDER BY id ASC",
            (workflow_id,),
        ).fetchall()
        return [pickle.loads(row[0]) for row in rows]

    def list_by_stage(self, workflow_id: str, stage: WorkflowStage) -> list[BaseArtifact]:
        rows = self._conn.execute(
            "SELECT payload FROM artifacts WHERE workflow_id = ? AND stage = ? ORDER BY id ASC",
            (workflow_id, stage.value),
        ).fetchall()
        return [pickle.loads(row[0]) for row in rows]

    def close(self) -> None:
        self._conn.close()
