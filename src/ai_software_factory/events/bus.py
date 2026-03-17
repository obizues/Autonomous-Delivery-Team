from __future__ import annotations

from ai_software_factory.domain.enums import EventType, WorkflowStage
from ai_software_factory.events.models import Event


class EventBus:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(self, workflow_id: str, event_type: EventType, stage: WorkflowStage, payload: dict[str, object] | None = None) -> Event:
        event = Event(workflow_id=workflow_id, event_type=event_type, stage=stage, payload=payload or {})
        self._events.append(event)
        return event

    def list_events(self, workflow_id: str | None = None) -> list[Event]:
        if workflow_id is None:
            return list(self._events)
        return [event for event in self._events if event.workflow_id == workflow_id]
