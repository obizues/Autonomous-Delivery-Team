from __future__ import annotations

import os

from ai_software_factory.agents.roles.architect import ArchitectAgent
from ai_software_factory.agents.roles.business_analyst import BusinessAnalystAgent
from ai_software_factory.agents.roles.engineer import EngineerAgent
from ai_software_factory.agents.roles.product_owner import ProductOwnerAgent
from ai_software_factory.agents.roles.test_engineer import TestEngineerAgent
from ai_software_factory.domain.enums import ArtifactStatus, WorkflowStage
from ai_software_factory.domain.models import BacklogItem
from ai_software_factory.execution.file_patch_engine import FilePatchEngine
from ai_software_factory.execution.repo_workspace import RepoWorkspaceManager
from ai_software_factory.execution.test_runner import PytestRunner
from ai_software_factory.events.bus import EventBus
from ai_software_factory.governance.approvals import ApprovalService
from ai_software_factory.governance.escalations import EscalationService
from ai_software_factory.planning.repo_change_planner import RepoChangePlanner
from ai_software_factory.persistence.artifact_store import InMemoryArtifactStore
from ai_software_factory.persistence.state_store import InMemoryStateStore
from ai_software_factory.workflow.engine import WorkflowEngine


def build_demo_backlog(seed_repo_name: str | None = None) -> BacklogItem:
    selected_seed_repo = seed_repo_name or os.getenv("ASF_SEED_REPO", "fake_upload_service")

    if selected_seed_repo == "simple_auth_service":
        return BacklogItem(
            workflow_id="",
            stage=WorkflowStage.BACKLOG_INTAKE,
            created_by="product_owner",
            status=ArtifactStatus.FINAL,
            title="Account Lockout After Repeated Login Failures",
            description=(
                "The authentication flow should detect repeated failed login attempts and lock the account "
                "after the configured threshold while preserving successful login behavior for valid credentials."
            ),
            problem_statement=(
                "The current auth service denies invalid credentials but never locks the account, leaving repeated "
                "credential guessing attempts unchecked."
            ),
            user_story=(
                "As a security-conscious operator, I want repeated failed logins to trigger account lockout so that "
                "brute-force attempts are contained quickly."
            ),
            business_value=(
                "Improves account security and reduces the blast radius of repeated credential attacks."
            ),
            acceptance_criteria=[
                "three failed login attempts trigger account lockout",
                "locked accounts return an explicit account_locked error",
                "valid credentials still authenticate successfully before lockout",
                "tests verify both lockout and successful authentication paths",
            ],
        )

    if selected_seed_repo == "data_pipeline":
        return BacklogItem(
            workflow_id="",
            stage=WorkflowStage.BACKLOG_INTAKE,
            created_by="product_owner",
            status=ArtifactStatus.FINAL,
            title="Reject Duplicate Pipeline Records With Explicit Reasons",
            description=(
                "The data pipeline should reject duplicate and schema-invalid records with explicit rejection reasons "
                "while continuing to process valid records."
            ),
            problem_statement=(
                "The current pipeline accepts valid records and rejects malformed ones, but it does not explain "
                "rejection reasons consistently and does not detect duplicate record identifiers."
            ),
            user_story=(
                "As a downstream data consumer, I want rejected records to include precise reasons so that I can "
                "repair bad input and prevent duplicate processing."
            ),
            business_value=(
                "Improves data quality, auditability, and safety of downstream processing."
            ),
            acceptance_criteria=[
                "duplicate ids are rejected",
                "rejected records include explicit reasons",
                "schema-invalid records are routed to rejected output",
                "valid records continue to process successfully",
            ],
        )

    return BacklogItem(
        workflow_id="",
        stage=WorkflowStage.BACKLOG_INTAKE,
        created_by="product_owner",
        status=ArtifactStatus.FINAL,
        title="Secure Document Upload Validation",
        description=(
            "Users should not be able to upload documents exceeding a maximum size. "
            "The upload flow should reject oversized files with a clear error payload while allowing valid uploads."
        ),
        problem_statement=(
            "The current upload service lacks explicit max-size validation and does not return clear "
            "error reasons for rejected oversized files."
        ),
        user_story=(
            "As a user, I want oversized uploads to be rejected immediately with a clear reason, "
            "so I can fix the file and retry quickly."
        ),
        business_value=(
            "Improves reliability and user trust by enforcing size policy at the upload boundary."
        ),
        acceptance_criteria=[
            "files larger than the limit are rejected",
            "error payload includes reason",
            "valid files continue to upload",
            "tests verify both accepted and rejected cases",
        ],
    )


def create_engine(seed_repo_name: str | None = None) -> WorkflowEngine:
    state_store = InMemoryStateStore()
    artifact_store = InMemoryArtifactStore()
    event_bus = EventBus()
    approval_service = ApprovalService()
    escalation_service = EscalationService()
    selected_seed_repo = seed_repo_name or os.getenv("ASF_SEED_REPO", "fake_upload_service")
    repo_workspace = RepoWorkspaceManager(seed_repo_name=selected_seed_repo)
    patch_engine = FilePatchEngine()
    planner = RepoChangePlanner()
    test_runner = PytestRunner()

    agents = {
        "product_owner": ProductOwnerAgent(),
        "business_analyst": BusinessAnalystAgent(),
        "architect": ArchitectAgent(),
        "engineer": EngineerAgent(
            repo_workspace=repo_workspace,
            planner=planner,
            patch_engine=patch_engine,
            event_bus=event_bus,
        ),
        "test_engineer": TestEngineerAgent(
            patch_engine=patch_engine,
            test_runner=test_runner,
            event_bus=event_bus,
        ),
    }

    return WorkflowEngine(
        state_store=state_store,
        artifact_store=artifact_store,
        event_bus=event_bus,
        agents=agents,
        approval_service=approval_service,
        escalation_service=escalation_service,
        max_revisions=3,
    )


def run_demo_workflow(seed_repo_name: str | None = None) -> dict[str, object]:
    engine = create_engine(seed_repo_name=seed_repo_name)
    backlog = build_demo_backlog(seed_repo_name)

    state = engine.start(backlog)
    final_state = engine.run_until_terminal(state.workflow_id)
    events = engine.event_bus.list_events(state.workflow_id)

    return {
        "workflow_id": final_state.workflow_id,
        "status": final_state.status.value,
        "final_stage": final_state.current_stage.value,
        "revision": final_state.revision,
        "artifact_count": len(final_state.artifact_ids),
        "pull_request_count": len(final_state.pull_request_ids),
        "review_feedback_count": len(final_state.review_feedback_ids),
        "approval_count": len(final_state.approval_ids),
        "event_count": len(events),
    }


if __name__ == "__main__":
    summary = run_demo_workflow()
    for key, value in summary.items():
        print(f"{key}: {value}")
