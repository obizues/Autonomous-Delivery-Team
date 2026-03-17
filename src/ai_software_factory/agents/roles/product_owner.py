from __future__ import annotations

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, WorkflowStage
from ai_software_factory.domain.models import BacklogItem, RequirementsSpec, ReviewFeedback, TestResult
from ai_software_factory.workflow.stage_result import StageResult


class ProductOwnerAgent(Agent):
    role = "product_owner"

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage
        wf_id = context.workflow_state.workflow_id

        if stage == WorkflowStage.BACKLOG_INTAKE:
            return StageResult(notes="Backlog intake complete.")

        if stage == WorkflowStage.PRODUCT_DEFINITION:
            backlog = context.latest(BacklogItem)
            title = backlog.title if backlog else "Feature"
            criteria = backlog.acceptance_criteria if backlog else []
            description = backlog.description if backlog else ""
            business_value = backlog.business_value if backlog else ""
            artifact = RequirementsSpec(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                summary=(
                    f"Product definition for '{title}'. "
                    f"Defines user-facing behaviour, acceptance criteria, and rollout value. {description}"
                ),
                functional_requirements=[
                    f"The feature must satisfy all acceptance criteria defined in the backlog item for '{title}'",
                    "The system must preserve existing successful behavior while adding the requested safeguards or validation rules",
                    "All rejection or failure paths introduced by this feature must return a clear, actionable reason",
                    f"Business value must remain visible in the resulting design and implementation: {business_value or 'improve reliability and user trust'}",
                ],
                edge_cases=[
                    "Boundary condition at the enforcement threshold must behave deterministically",
                    "Repeated invalid attempts must not corrupt successful paths",
                    "Structured error payload must remain stable for callers and tests",
                    "State updates introduced by the feature must be reversible or safely reset after success",
                ] + ([f"AC gap: {c}" for c in criteria if "flag" in c.lower() or "reject" in c.lower()]),
            )
            return StageResult(produced_artifacts=[artifact], notes="Product definition and acceptance criteria created.")

        if stage == WorkflowStage.PRODUCT_ACCEPTANCE_GATE:
            latest_test = context.latest(TestResult)
            accepted = latest_test is not None and latest_test.passed
            decision = Decision.APPROVED if accepted else Decision.REQUEST_CHANGES

            backlog = context.latest(BacklogItem)
            criteria = backlog.acceptance_criteria if backlog else []
            acceptance = ReviewFeedback(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=context.workflow_state.revision,
                reviewer=self.role,
                decision=decision,
                comments=(
                    f"All acceptance criteria verified for '{backlog.title if backlog else 'Feature'}'. "
                    "The requested safeguards, explicit responses, and successful-path behavior are confirmed working."
                    if accepted else
                    "Test results not present or failing. Product acceptance withheld pending successful test gate."
                ),
                issues_identified=[] if accepted else ["Test gate must pass before product acceptance"],
                suggested_changes=(
                    [f"Verify AC: {c}" for c in criteria]
                    if accepted else ["Re-run implementation and test stages"]
                ),
            )
            return StageResult(
                produced_artifacts=[acceptance],
                decision=decision,
                notes="Product accepted." if accepted else "Product acceptance failed — revision required.",
            )

        return StageResult(notes=f"No Product Owner action for stage {stage.value}.")
