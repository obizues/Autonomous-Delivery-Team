from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.domain.enums import Decision, EscalationStatus, WorkflowStage


@dataclass
class BacklogItem(BaseArtifact):
    title: str = ""
    description: str = ""
    problem_statement: str = ""
    user_story: str = ""
    business_value: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class RequirementsSpec(BaseArtifact):
    summary: str = ""
    functional_requirements: list[str] = field(default_factory=list)
    non_functional_requirements: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    inputs_outputs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ArchitectureSpec(BaseArtifact):
    overview: str = ""
    components: list[str] = field(default_factory=list)
    api_changes: list[str] = field(default_factory=list)
    data_flow: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    security_considerations: list[str] = field(default_factory=list)
    scalability_considerations: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class CodeImplementation(BaseArtifact):
    summary: str = ""
    approach: str = ""
    workspace_path: str = ""
    files_changed: list[str] = field(default_factory=list)
    written_source_files: list[str] = field(default_factory=list)
    key_algorithms: list[str] = field(default_factory=list)
    implementation_notes: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class PullRequest(BaseArtifact):
    title: str = ""
    description: str = ""
    implementation_artifact_id: str | None = None
    files_modified: list[str] = field(default_factory=list)
    architecture_alignment: str = ""
    test_coverage: str = ""
    known_limitations: list[str] = field(default_factory=list)
    linked_review_ids: list[str] = field(default_factory=list)


@dataclass
class ReviewFeedback(BaseArtifact):
    reviewer: str = ""
    decision: Decision = Decision.APPROVED
    comments: str = ""
    issues_identified: list[str] = field(default_factory=list)
    suggested_changes: list[str] = field(default_factory=list)
    pull_request_id: str | None = None


@dataclass
class TestResult(BaseArtifact):
    passed: bool = False
    total_cases: int = 0
    failed_cases: int = 0
    failures_reduced: int = 0
    no_new_failures: bool = True
    stable_pass_streak: int = 0
    regression_detected: bool = False
    new_failures: list[str] = field(default_factory=list)
    targeted_tests: list[str] = field(default_factory=list)
    targeted_command: str = ""
    targeted_exit_code: int = 0
    workspace_path: str = ""
    run_log_path: str = ""
    test_command: str = ""
    output: str = ""
    stdout: str = ""
    stderr: str = ""
    failing_tests: list[str] = field(default_factory=list)
    generated_test_files: list[str] = field(default_factory=list)
    unit_tests: list[str] = field(default_factory=list)
    integration_tests: list[str] = field(default_factory=list)
    edge_case_coverage: list[str] = field(default_factory=list)
    coverage_estimate: str = ""
    details: list[str] = field(default_factory=list)
    pull_request_id: str | None = None


@dataclass
class ApprovalRecord:
    workflow_id: str
    stage: WorkflowStage
    reviewer: str
    decision: Decision
    comments: str
    approval_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EscalationRecord:
    workflow_id: str
    reason: str
    raised_by: str
    escalation_id: str = field(default_factory=lambda: str(uuid4()))
    status: EscalationStatus = EscalationStatus.OPEN
    human_response: str | None = None
    resolved_at: datetime | None = None
