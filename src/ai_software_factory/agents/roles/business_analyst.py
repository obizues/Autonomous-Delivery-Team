from __future__ import annotations

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus
from ai_software_factory.domain.models import BacklogItem, RequirementsSpec
from ai_software_factory.workflow.stage_result import StageResult


class BusinessAnalystAgent(Agent):
    role = "business_analyst"

    def act(self, context: AgentContext) -> StageResult:
        backlog = context.latest(BacklogItem)
        title = backlog.title if backlog else "Feature"
        description = backlog.description if backlog else ""
        problem_statement = backlog.problem_statement if backlog else ""
        user_story = backlog.user_story if backlog else ""
        acceptance = backlog.acceptance_criteria if backlog else []
        artifact = RequirementsSpec(
            workflow_id=context.workflow_state.workflow_id,
            stage=context.workflow_state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            summary=(
                f"Detailed requirements for '{title}'. {description} Problem focus: {problem_statement}"
            ),
            functional_requirements=[
                f"FR-01: The implementation must satisfy the requested user story: {user_story or 'deliver the requested behavior safely'}",
                "FR-02: Existing successful behavior must remain intact for valid input paths",
                "FR-03: Invalid or rejected paths must return explicit structured reasons that tests can assert",
                "FR-04: Newly introduced rules must be deterministic and repeatable across multiple runs",
            ] + [
                f"AC-{index + 1:02d}: {criterion}"
                for index, criterion in enumerate(acceptance)
            ],
            non_functional_requirements=[
                "NFR-01: The feature must be testable using local deterministic pytest execution",
                "NFR-02: Rule evaluation must be side-effect aware and safe to repeat in revision loops",
                "NFR-03: Error responses must be stable enough for automated assertions",
                "NFR-04: The solution should minimize unrelated code changes outside the targeted module set",
                "NFR-05: The implementation must remain readable enough for semantic planner targeting",
            ],
            edge_cases=[
                "Boundary values around thresholds must behave consistently",
                "Repeated invalid input attempts must preserve valid-path behavior",
                "Partial state introduced during failed processing must not corrupt future attempts",
                "Caller-visible response shape must remain explicit for both success and failure paths",
            ],
            inputs_outputs=[
                "Input: domain-specific request arguments defined by the seed repo's public function surface",
                "Output (success): existing success payload remains intact unless backlog explicitly changes it",
                "Output (rejection): explicit status or error reason is returned for rejected paths",
                "Output (review/exception path): caller receives deterministic structured feedback",
            ],
            dependencies=[
                "Local Python source modules in the seed repo",
                "pytest-based regression validation",
                "Semantic planner outputs (target symbols, confidence, intent classification)",
                "Patch engine with syntax validation and rollback",
            ],
        )
        return StageResult(produced_artifacts=[artifact], notes="Requirements analysis completed.")
