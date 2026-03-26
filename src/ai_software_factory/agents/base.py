from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.workflow.stage_result import StageResult
from ai_software_factory.workflow.state import WorkflowState

ArtifactType = TypeVar("ArtifactType", bound=BaseArtifact)



@dataclass
class AgentContext:
    workflow_state: WorkflowState
    artifacts: list[BaseArtifact]
    agent_config: dict = None

    def latest(self, artifact_type: type[ArtifactType]) -> ArtifactType | None:
        for artifact in reversed(self.artifacts):
            if isinstance(artifact, artifact_type):
                return artifact
        return None


class Agent(ABC):
    role: str

    @abstractmethod
    def act(self, context: AgentContext) -> StageResult:
        raise NotImplementedError
