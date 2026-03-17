from __future__ import annotations

from datetime import datetime, timezone

from ai_software_factory.domain.enums import EscalationStatus
from ai_software_factory.domain.models import EscalationRecord


class EscalationService:
    def __init__(self) -> None:
        self._escalations: dict[str, EscalationRecord] = {}

    def raise_escalation(self, workflow_id: str, reason: str, raised_by: str) -> EscalationRecord:
        record = EscalationRecord(workflow_id=workflow_id, reason=reason, raised_by=raised_by)
        self._escalations[record.escalation_id] = record
        return record

    def resolve_escalation(self, escalation_id: str, human_response: str) -> EscalationRecord | None:
        escalation = self._escalations.get(escalation_id)
        if escalation is None:
            return None
        escalation.status = EscalationStatus.RESOLVED
        escalation.human_response = human_response
        escalation.resolved_at = datetime.now(timezone.utc)
        return escalation

    def get(self, escalation_id: str) -> EscalationRecord | None:
        return self._escalations.get(escalation_id)
