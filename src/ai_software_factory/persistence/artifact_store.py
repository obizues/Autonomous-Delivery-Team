from __future__ import annotations

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.domain.enums import WorkflowStage


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
