"""Renders domain artifacts as structured, human-readable markdown documents."""
from __future__ import annotations

from ai_software_factory.domain.base import BaseArtifact
from ai_software_factory.domain.enums import Decision, WorkflowStage
from ai_software_factory.domain.models import (
    ArchitectureSpec,
    BacklogItem,
    CodeImplementation,
    EscalationArtifact,
    HumanIntervention,
    PullRequest,
    RequirementsSpec,
    ReviewFeedback,
    TestResult,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _h(level: int, text: str) -> str:
    return f"{'#' * level} {text}\n"


def _field(label: str, value: str) -> str:
    return f"**{label}:** {value or '_Not specified_'}\n"


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "_None listed._\n"
    return "\n".join(f"- {item}" for item in items) + "\n"


def _section(title: str, body: str) -> str:
    return f"\n{_h(2, title)}\n{body}"


def _divider() -> str:
    return "\n---\n"


# ---------------------------------------------------------------------------
# Per-artifact-type renderers
# Each returns (slug, markdown_content).
# slug is used to build the filename alongside the JSON artifact.
# ---------------------------------------------------------------------------

def _render_backlog_item(a: BacklogItem) -> tuple[str, str]:
    md = _h(1, f"Product Brief: {a.title or 'Untitled'}")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Problem Statement", f"{a.problem_statement or '_Not provided._'}\n")
    md += _section("User Story", f"{a.user_story or '_Not provided._'}\n")
    md += _section("Business Value", f"{a.business_value or '_Not provided._'}\n")
    md += _section("Acceptance Criteria", _bullet_list(a.acceptance_criteria))
    return "product_brief", md


def _render_requirements_spec_po(a: RequirementsSpec) -> tuple[str, str]:
    md = _h(1, "Product Brief")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Summary", f"{a.summary or '_Not provided._'}\n")
    md += _section("Functional Requirements", _bullet_list(a.functional_requirements))
    md += _section("Edge Cases", _bullet_list(a.edge_cases))
    return "product_brief", md


def _render_requirements_spec_ba(a: RequirementsSpec) -> tuple[str, str]:
    md = _h(1, "Requirements Specification")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Summary", f"{a.summary or '_Not provided._'}\n")
    md += _section("Functional Requirements", _bullet_list(a.functional_requirements))
    md += _section("Non-Functional Requirements", _bullet_list(a.non_functional_requirements))
    md += _section("Edge Cases", _bullet_list(a.edge_cases))
    md += _section("Inputs / Outputs", _bullet_list(a.inputs_outputs))
    md += _section("Dependencies", _bullet_list(a.dependencies))
    return "requirements_spec", md


def _render_architecture_spec(a: ArchitectureSpec) -> tuple[str, str]:
    md = _h(1, "Architecture Design")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("System Overview", f"{a.overview or '_Not provided._'}\n")
    md += _section("Components", _bullet_list(a.components))
    md += _section("API Changes", _bullet_list(a.api_changes))
    md += _section("Data Flow", _bullet_list(a.data_flow))
    md += _section("Architectural Decisions", _bullet_list(a.decisions))
    md += _section("Security Considerations", _bullet_list(a.security_considerations))
    md += _section("Scalability Considerations", _bullet_list(a.scalability_considerations))
    md += _section("Risks", _bullet_list(a.risks))
    return "architecture_design", md


def _render_code_implementation(a: CodeImplementation) -> tuple[str, str]:
    md = _h(1, "Implementation Plan")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Summary", f"{a.summary or '_Not provided._'}\n")
    md += _section("Generated Workspace", f"{a.workspace_path or '_Not provided._'}\n")
    md += _section("Implementation Approach", f"{a.approach or '_Not provided._'}\n")
    md += _section("Files / Components Affected", _bullet_list(a.files_changed))
    md += _section("Written Source Files", _bullet_list(a.written_source_files))
    md += _section("Key Algorithms or Logic", _bullet_list(a.key_algorithms))
    md += _section("Implementation Notes", _bullet_list(a.implementation_notes))
    md += _section("Risks", _bullet_list(a.risks))
    return "implementation_plan", md


def _render_pull_request(a: PullRequest) -> tuple[str, str]:
    md = _h(1, f"Pull Request: {a.title or 'Untitled'}")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Feature Summary", f"{a.description or '_Not provided._'}\n")
    md += _section("Implementation Overview", f"Implements artifact `{a.implementation_artifact_id or 'N/A'}`.\n")
    md += _section("Files Modified", _bullet_list(a.files_modified))
    md += _section("Architecture Alignment", f"{a.architecture_alignment or '_Not assessed._'}\n")
    md += _section("Test Coverage", f"{a.test_coverage or '_Not assessed._'}\n")
    md += _section("Known Limitations", _bullet_list(a.known_limitations))
    return "pull_request", md


def _render_code_review(a: ReviewFeedback) -> tuple[str, str]:
    verdict = f"**{a.decision.value}**"
    md = _h(1, "Code Review")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Reviewer: {a.reviewer}*\n"
    md += _divider()
    md += _section("Reviewer", f"{a.reviewer}\n")
    md += _section("Summary", f"{a.comments or '_No comments provided._'}\n")
    md += _section("Issues Identified", _bullet_list(a.issues_identified))
    md += _section("Suggested Changes", _bullet_list(a.suggested_changes))
    md += _section("Decision", f"{verdict}\n")
    return "code_review", md


def _render_test_report(a: TestResult) -> tuple[str, str]:
    status = "PASSED" if a.passed else "FAILED"
    md = _h(1, f"Test Report — {status}")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Created by: {a.created_by}*\n"
    md += _divider()
    md += _section("Summary", f"Total: {a.total_cases} · Failed: {a.failed_cases} · **{status}**\n")
    md += _section("Execution", f"Command: `{a.test_command or 'N/A'}`\n\nWorkspace: `{a.workspace_path or 'N/A'}`\n\nRun log: `{a.run_log_path or 'N/A'}`\n")
    md += _section("Failing Tests", _bullet_list(a.failing_tests))
    md += _section("Generated Test Files", _bullet_list(a.generated_test_files))
    md += _section("Unit Tests", _bullet_list(a.unit_tests))
    md += _section("Integration Tests", _bullet_list(a.integration_tests))
    md += _section("Edge Case Coverage", _bullet_list(a.edge_case_coverage))
    md += _section("Test Details", _bullet_list(a.details))
    if a.stdout:
        md += _section("pytest stdout", f"```text\n{a.stdout[-4000:]}\n```\n")
    if a.stderr:
        md += _section("pytest stderr", f"```text\n{a.stderr[-4000:]}\n```\n")
    md += _section("Coverage Estimate", f"{a.coverage_estimate or '_Not provided._'}\n")
    return "test_report", md


def _render_escalation(a: EscalationArtifact) -> tuple[str, str]:
    md = _h(1, "Workflow Escalation")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Raised by: {a.raised_by}*\n"
    md += _divider()
    md += _section("Status", f"{a.escalation_status.value}\n")
    md += _section("Reason", f"{a.reason or '_Not provided._'}\n")
    md += _section("Human Response", f"{a.human_response or '_Awaiting human response._'}\n")
    md += _section("Resolution Summary", f"{a.resolution_summary or '_Not resolved yet._'}\n")
    return "workflow_escalation", md


def _render_human_intervention(a: HumanIntervention) -> tuple[str, str]:
    md = _h(1, "Human Intervention")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Responder: {a.responder}*\n"
    md += _divider()
    md += _section("Requested Outcome", f"{a.desired_outcome}\n")
    md += _section("Resume Stage", f"{a.resume_stage.value}\n")
    md += _section("Response", f"{a.response or '_No response provided._'}\n")
    md += _section("Resolution Notes", _bullet_list(a.resolution_notes))
    return "human_intervention", md


def _render_acceptance_decision(a: ReviewFeedback) -> tuple[str, str]:
    verdict = f"**{a.decision.value}**"
    md = _h(1, "Acceptance Decision")
    md += f"\n> *Revision {a.version} · Stage: {a.stage.value} · Reviewer: {a.reviewer}*\n"
    md += _divider()
    md += _section("Acceptance Criteria Review", _bullet_list(a.issues_identified) if a.issues_identified else "_All criteria met._\n")
    md += _section("Product Owner Decision", f"{verdict}\n")
    md += _section("Notes", f"{a.comments or '_None._'}\n")
    checklist_title = "Acceptance Checklist" if a.decision == Decision.APPROVED else "Suggested Changes"
    md += _section(checklist_title, _bullet_list(a.suggested_changes) if a.suggested_changes else "_None._\n")
    return "acceptance_decision", md


_REVIEW_GATE_STAGES = {
    WorkflowStage.ARCHITECTURE_REVIEW_GATE,
    WorkflowStage.PEER_CODE_REVIEW_GATE,
}


def render_artifact_markdown(artifact: BaseArtifact) -> tuple[str, str] | None:
    """Return *(slug, markdown_content)* for *artifact*, or ``None`` if unsupported.

    The caller should save the content as ``{artifact_id}_{slug}.md`` beside the
    existing ``{artifact_id}_{ArtifactType}.json`` file.
    """
    if isinstance(artifact, BacklogItem):
        return _render_backlog_item(artifact)

    if isinstance(artifact, RequirementsSpec):
        if artifact.created_by == "product_owner":
            return _render_requirements_spec_po(artifact)
        return _render_requirements_spec_ba(artifact)

    if isinstance(artifact, ArchitectureSpec):
        return _render_architecture_spec(artifact)

    if isinstance(artifact, CodeImplementation):
        return _render_code_implementation(artifact)

    if isinstance(artifact, PullRequest):
        return _render_pull_request(artifact)

    if isinstance(artifact, ReviewFeedback):
        if artifact.stage == WorkflowStage.PRODUCT_ACCEPTANCE_GATE:
            return _render_acceptance_decision(artifact)
        if artifact.stage in _REVIEW_GATE_STAGES:
            return _render_code_review(artifact)
        # TEST_VALIDATION_GATE reviewer feedback — rolled into the TestResult report
        return _render_code_review(artifact)

    if isinstance(artifact, TestResult):
        return _render_test_report(artifact)

    if isinstance(artifact, EscalationArtifact):
        return _render_escalation(artifact)

    if isinstance(artifact, HumanIntervention):
        return _render_human_intervention(artifact)

    return None
