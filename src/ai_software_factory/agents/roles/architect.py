from __future__ import annotations

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, WorkflowStage
from ai_software_factory.domain.models import ArchitectureSpec, BacklogItem, PullRequest, ReviewFeedback
from ai_software_factory.workflow.stage_result import StageResult


class ArchitectAgent(Agent):
    role = "architect"

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage
        wf_id = context.workflow_state.workflow_id
        revision = context.workflow_state.revision

        if stage == WorkflowStage.ARCHITECTURE_DESIGN:
            backlog = context.latest(BacklogItem)
            title = backlog.title if backlog else "Feature"
            description = backlog.description if backlog else ""
            problem_statement = backlog.problem_statement if backlog else ""
            artifact = ArchitectureSpec(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                overview=(
                    f"'{title}' is implemented as a small modular Python service with focused domain modules, "
                    "deterministic business rules, and a test-first revision loop. "
                    f"Primary problem addressed: {problem_statement or description}"
                ),
                components=[
                    "Seed repo source modules — existing domain logic targeted by semantic planner",
                    "Generated test modules — encode acceptance criteria as executable pytest checks",
                    "Patch engine — applies whole-file or function-level edits with syntax validation and rollback",
                    "Semantic planner — maps failing tests to files and symbols using imports and traceback hints",
                    "Workflow engine — coordinates revision loops, approvals, and escalations",
                ],
                api_changes=[
                    "Public function surface remains aligned with the seed repo unless acceptance criteria require a contract change",
                    "Structured success and failure payloads must remain stable for automated tests",
                    "Module-level business rules may be tightened to enforce validation, lockout, or rejection semantics",
                ],
                data_flow=[
                    "Backlog item -> planner intent classification -> target files and symbols",
                    "Generated tests -> pytest execution -> failing test extraction",
                    "Failing tests + traceback hints -> semantic localization -> change plan",
                    "Engineer patch strategy -> source edits -> syntax validation and rollback if needed",
                    "Re-run targeted and full pytest suites -> approve revision or request changes",
                ],
                decisions=[
                    "ADR-01: Acceptance criteria are converted into executable tests before final approval",
                    "ADR-02: Semantic targeting narrows edits to relevant files and symbols where possible",
                    "ADR-03: Syntax validation and rollback protect the sandbox from broken intermediate patches",
                    "ADR-04: Regression-aware revision policy escalates if failures stall or regress near limits",
                    "ADR-05: Repo-specific deterministic strategies provide reliable convergence for demo seeds",
                ],
                security_considerations=[
                    "Rejection and validation logic must fail closed and return explicit reasons",
                    "State-tracking features such as lockout counters must reset safely after successful operations",
                    "Duplicate or invalid inputs must not silently pass through to successful output sets",
                    "Sandbox execution isolates patching from the original seed repo",
                ],
                scalability_considerations=[
                    "Semantic indexing currently targets Python repos and small deterministic demos efficiently",
                    "Targeted test execution reduces feedback time before running the full suite",
                    "Repo profiles can be expanded with additional deterministic strategies as new seeds are added",
                    "Full autonomy for arbitrary repos will require more generalized synthesis beyond fixed demo profiles",
                ],
                risks=[
                    "RISK-01: Heuristic failure localization may still miss the correct symbol in more complex repos",
                    "RISK-02: Profile-specific strategies are deterministic but not yet fully generalized across arbitrary architectures",
                    "RISK-03: Acceptance tests may overfit to expected payload shapes if backlog wording is ambiguous",
                    "RISK-04: Larger repos may need deeper indexing and patch planning than the current demo loop provides",
                ],
            )
            return StageResult(produced_artifacts=[artifact], notes="Architecture design completed.")

        if stage == WorkflowStage.ARCHITECTURE_REVIEW_GATE:
            pr = context.latest(PullRequest)
            if pr is None:
                decision = Decision.REQUEST_CHANGES
                comments = "Architecture review blocked: no pull request artifact found for this revision."
                issues = ["Pull request artifact is missing for the current revision"]
                suggestions = ["Engineer must submit a PullRequest artifact before architecture review can proceed"]
            else:
                decision = Decision.APPROVED
                comments = (
                    "Architecture review passed. Implementation aligns with the modular repo-aware workflow, "
                    "semantic targeting, deterministic rule enforcement, and revision-safe patching strategy."
                )
                issues = []
                suggestions = []

            review = ReviewFeedback(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer=self.role,
                decision=decision,
                comments=comments,
                issues_identified=issues,
                suggested_changes=suggestions,
                pull_request_id=pr.artifact_id if pr else None,
            )
            return StageResult(produced_artifacts=[review], decision=decision, notes="Architecture review complete.")

        return StageResult(notes=f"No Architect action for stage {stage.value}.")
