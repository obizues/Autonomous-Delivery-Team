from __future__ import annotations

from ai_software_factory.domain.enums import Decision, WorkflowStage
from ai_software_factory.domain.models import ApprovalRecord


class ApprovalService:
    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRecord] = {}

    def create_approval(
        self,
        workflow_id: str,
        stage: WorkflowStage,
        reviewer: str,
        decision: Decision,
        comments: str,
    ) -> ApprovalRecord:
        record = ApprovalRecord(
            workflow_id=workflow_id,
            stage=stage,
            reviewer=reviewer,
            decision=decision,
            comments=comments,
        )
        self._approvals[record.approval_id] = record
        return record

    def get(self, approval_id: str) -> ApprovalRecord | None:
        return self._approvals.get(approval_id)
