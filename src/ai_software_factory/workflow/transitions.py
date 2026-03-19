from __future__ import annotations

from ai_software_factory.domain.enums import WorkflowStage

WORKFLOW_SEQUENCE: list[WorkflowStage] = [
    WorkflowStage.BACKLOG_INTAKE,
    WorkflowStage.PRODUCT_DEFINITION,
    WorkflowStage.REQUIREMENTS_ANALYSIS,
    WorkflowStage.ARCHITECTURE_DESIGN,
    WorkflowStage.IMPLEMENTATION,
    WorkflowStage.PULL_REQUEST_CREATED,
    WorkflowStage.MERGE_CONFLICT_GATE,
    WorkflowStage.ARCHITECTURE_REVIEW_GATE,
    WorkflowStage.PEER_CODE_REVIEW_GATE,
    WorkflowStage.TEST_VALIDATION_GATE,
    WorkflowStage.PRODUCT_ACCEPTANCE_GATE,
    WorkflowStage.DONE,
]

REVIEW_GATES: set[WorkflowStage] = {
    WorkflowStage.MERGE_CONFLICT_GATE,
    WorkflowStage.ARCHITECTURE_REVIEW_GATE,
    WorkflowStage.PEER_CODE_REVIEW_GATE,
    WorkflowStage.TEST_VALIDATION_GATE,
    WorkflowStage.PRODUCT_ACCEPTANCE_GATE,
}

STAGE_TO_ROLE: dict[WorkflowStage, str] = {
    WorkflowStage.BACKLOG_INTAKE: "product_owner",
    WorkflowStage.PRODUCT_DEFINITION: "product_owner",
    WorkflowStage.REQUIREMENTS_ANALYSIS: "business_analyst",
    WorkflowStage.ARCHITECTURE_DESIGN: "architect",
    WorkflowStage.IMPLEMENTATION: "engineer",
    WorkflowStage.PULL_REQUEST_CREATED: "engineer",
    WorkflowStage.MERGE_CONFLICT_GATE: "engineer",
    WorkflowStage.ARCHITECTURE_REVIEW_GATE: "architect",
    WorkflowStage.PEER_CODE_REVIEW_GATE: "engineer",
    WorkflowStage.TEST_VALIDATION_GATE: "test_engineer",
    WorkflowStage.PRODUCT_ACCEPTANCE_GATE: "product_owner",
}


def is_review_gate(stage: WorkflowStage) -> bool:
    return stage in REVIEW_GATES


def default_next_stage(stage: WorkflowStage) -> WorkflowStage:
    current_index = WORKFLOW_SEQUENCE.index(stage)
    if current_index + 1 >= len(WORKFLOW_SEQUENCE):
        return WorkflowStage.DONE
    return WORKFLOW_SEQUENCE[current_index + 1]
