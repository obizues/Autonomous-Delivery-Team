from __future__ import annotations
# Concrete implementations for testing
class StateStore:
    def __init__(self):
        self._store = {}
    def save(self, state):
        self._store[getattr(state, 'workflow_id', None)] = state
    def load(self, workflow_id):
        return self._store.get(workflow_id)

class ArtifactStore:
    def __init__(self):
        self._artifacts = {}
    def save(self, artifact):
        self._artifacts[getattr(artifact, 'artifact_id', None)] = artifact
    def load(self, artifact_id):
        return self._artifacts.get(artifact_id)
import pickle
import sqlite3
from pathlib import Path
from typing import Protocol

from ai_software_factory.workflow.state import WorkflowState


class StateStore(Protocol):
    def save(self, state: WorkflowState) -> None:
        ...

    def load(self, workflow_id: str) -> WorkflowState:
        ...


class InMemoryStateStore:
    def __init__(self) -> None:
        self._states: dict[str, WorkflowState] = {}

    def save(self, state: WorkflowState) -> None:
        self._states[state.workflow_id] = state

    def load(self, workflow_id: str) -> WorkflowState:
        return self._states[workflow_id]


class SQLiteStateStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_states (
                workflow_id TEXT PRIMARY KEY,
                payload BLOB NOT NULL
            )
            """
        )
        self._conn.commit()

    def save(self, state: WorkflowState) -> None:
        payload = sqlite3.Binary(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
        self._conn.execute(
            """
            INSERT INTO workflow_states (workflow_id, payload)
            VALUES (?, ?)
            ON CONFLICT(workflow_id) DO UPDATE SET payload=excluded.payload
            """,
            (state.workflow_id, payload),
        )
        self._conn.commit()

    def load(self, workflow_id: str) -> WorkflowState:
        row = self._conn.execute(
            "SELECT payload FROM workflow_states WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        if row is None:
            raise KeyError(workflow_id)
        return pickle.loads(row[0])

    def close(self) -> None:
        self._conn.close()
