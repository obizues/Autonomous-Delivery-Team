from __future__ import annotations

from ai_software_factory.workflow.state import WorkflowState


class InMemoryStateStore:
    def __init__(self) -> None:
        self._states: dict[str, WorkflowState] = {}

    def save(self, state: WorkflowState) -> None:
        self._states[state.workflow_id] = state

    def load(self, workflow_id: str) -> WorkflowState:
        return self._states[workflow_id]
