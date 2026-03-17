from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ai_software_factory.domain.enums import EventType, WorkflowStage


@dataclass
class Event:
    workflow_id: str
    event_type: EventType
    stage: WorkflowStage
    payload: dict[str, object] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
