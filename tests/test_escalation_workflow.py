import pytest
from ai_software_factory.workflow.engine import WorkflowEngine
from ai_software_factory.persistence.state_store import InMemoryStateStore
from ai_software_factory.persistence.artifact_store import InMemoryArtifactStore
from ai_software_factory.events.bus import EventBus
from ai_software_factory.governance.approvals import ApprovalService
from ai_software_factory.governance.escalations import EscalationService
from ai_software_factory.domain.models import BacklogItem

class DummyAgent:
    class Result:
        def __init__(self, produced_artifacts=None, escalation_request=None, decision=None, notes=""):
            self.produced_artifacts = produced_artifacts or []
            self.escalation_request = escalation_request
            self.decision = decision
            self.notes = notes
    def act(self, context):
        state = context.workflow_state
        if hasattr(state, "status"):
            state.status = "COMPLETED"
        if hasattr(state, "stage_history") and hasattr(state, "current_stage"):
            state.stage_history.append(state.current_stage)
        return DummyAgent.Result()

def test_escalation_workflow():
    state_store = InMemoryStateStore()
    artifact_store = InMemoryArtifactStore()
    event_bus = EventBus()
    approval_service = ApprovalService()
    escalation_service = EscalationService()
    agents = {
        "product_owner": DummyAgent(),
        "business_analyst": DummyAgent(),
        "architect": DummyAgent(),
        "engineer": DummyAgent(),
        "test_engineer": DummyAgent()
    }
    engine = WorkflowEngine(
        state_store,
        artifact_store,
        event_bus,
        agents,
        approval_service,
        escalation_service,
    )
    backlog_item = BacklogItem(
        workflow_id="test_workflow_escalation",
        stage="BACKLOG_INTAKE",
        created_by="ProductOwner",
        artifact_id="test_backlog_escalation",
        title="Test Backlog Escalation",
        description="Test description",
        problem_statement="Test problem",
        user_story="Test story",
        business_value="Test value"
    )
    state = engine.start(backlog_item)
    # Simulate escalation
    state.status = "ESCALATED"
    # Explicitly create escalation artifact
    from ai_software_factory.domain.models import EscalationArtifact
    from ai_software_factory.domain.enums import WorkflowStage, ArtifactStatus
    escalation_artifact_id = "escalation_artifact_1"
    escalation_artifact = EscalationArtifact(
        workflow_id=state.workflow_id,
        stage=state.current_stage,
        created_by="ProductOwner",
        artifact_id=escalation_artifact_id,
        status=ArtifactStatus.DRAFT,
        reason="Test escalation",
        raised_by="ProductOwner"
    )
    artifact_store.save(escalation_artifact)
    resumed = engine.resume_from_escalation(
        workflow_id=state.workflow_id,
        human_response="Resume work",
        responder="human_operator",
        resume_stage=None,
        response_template="Minimal safe patch set",
        resume_max_steps=10,
    )
    assert resumed.status == "IN_PROGRESS"
    assert len(resumed.artifact_ids) > 0
