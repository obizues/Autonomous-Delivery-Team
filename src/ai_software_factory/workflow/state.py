
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ai_software_factory.domain.enums import WorkflowStage, WorkflowStatus


@dataclass
class WorkflowState:
    backlog_item_id: str
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    current_stage: WorkflowStage = WorkflowStage.BACKLOG_INTAKE
    status: WorkflowStatus = WorkflowStatus.IN_PROGRESS
    revision: int = 1
    stage_history: list[WorkflowStage] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    pull_request_ids: list[str] = field(default_factory=list)
    review_feedback_ids: list[str] = field(default_factory=list)
    approval_ids: list[str] = field(default_factory=list)
    escalation_ids: list[str] = field(default_factory=list)
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))