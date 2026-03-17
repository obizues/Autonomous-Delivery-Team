from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ai_software_factory.domain.enums import ArtifactStatus, WorkflowStage


@dataclass
class BaseArtifact:
    workflow_id: str
    stage: WorkflowStage
    created_by: str
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ArtifactStatus = ArtifactStatus.DRAFT
