
import pytest
from ai_software_factory.persistence.state_store import InMemoryStateStore
from ai_software_factory.persistence.artifact_store import InMemoryArtifactStore
from ai_software_factory.workflow.state import WorkflowState
from ai_software_factory.domain.base import BaseArtifact

def test_state_store_persistence():
    store = InMemoryStateStore()
    workflow_id = "wf123"
    state = WorkflowState(backlog_item_id="test_backlog", workflow_id=workflow_id, status="IN_PROGRESS")
    store.save(state)
    loaded = store.load(workflow_id)
    assert loaded.workflow_id == workflow_id
    assert loaded.status == "IN_PROGRESS"

def test_artifact_store_persistence():
    store = InMemoryArtifactStore()
    workflow_id = "wf123"
    artifact = BaseArtifact(
        workflow_id=workflow_id,
        stage="BACKLOG_INTAKE",
        created_by="test_user",
        artifact_id="a1"
    )
    store.save(artifact)
    artifacts = store.list_by_workflow(workflow_id)
    assert any(a.artifact_id == "a1" for a in artifacts)

