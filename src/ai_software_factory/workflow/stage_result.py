from __future__ import annotations

from dataclasses import dataclass, field

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.domain.enums import Decision, WorkflowStage


@dataclass
class EscalationRequest:
    reason: str
    raised_by: str


@dataclass
class StageResult:
    produced_artifacts: list[BaseArtifact] = field(default_factory=list)
    decision: Decision | None = None
    notes: str = ""
    escalation_request: EscalationRequest | None = None
    next_stage_override: WorkflowStage | None = None
