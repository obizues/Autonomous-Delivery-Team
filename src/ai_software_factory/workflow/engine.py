from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import Decision, EventType, WorkflowStage, WorkflowStatus
from ai_software_factory.domain.models import BacklogItem, PullRequest, ReviewFeedback, TestResult
from ai_software_factory.events.bus import EventBus
from ai_software_factory.governance.approvals import ApprovalService
from ai_software_factory.governance.escalations import EscalationService
from ai_software_factory.persistence.artifact_store import InMemoryArtifactStore
from ai_software_factory.persistence.state_store import InMemoryStateStore
from ai_software_factory.workflow.state import WorkflowState
from ai_software_factory.workflow.transitions import STAGE_TO_ROLE, default_next_stage, is_review_gate


class WorkflowEngine:
    def __init__(
        self,
        state_store: InMemoryStateStore,
        artifact_store: InMemoryArtifactStore,
        event_bus: EventBus,
        agents: dict[str, Agent],
        approval_service: ApprovalService,
        escalation_service: EscalationService,
        max_revisions: int = 3,
    ) -> None:
        self.state_store = state_store
        self.artifact_store = artifact_store
        self.event_bus = event_bus
        self.agents = agents
        self.approval_service = approval_service
        self.escalation_service = escalation_service
        self.max_revisions = max_revisions

    def _recent_test_results(self, workflow_id: str, count: int = 3) -> list[TestResult]:
        artifacts = self.artifact_store.list_by_workflow(workflow_id)
        tests = [artifact for artifact in artifacts if isinstance(artifact, TestResult)]
        return tests[-count:]

    def _build_progress_summary(self, workflow_id: str) -> dict[str, object]:
        tests = self._recent_test_results(workflow_id, count=3)
        if not tests:
            return {
                "failures_reduced": 0,
                "no_new_failures": True,
                "stable_pass_streak": 0,
                "stalled": False,
            }

        latest = tests[-1]
        previous = tests[-2] if len(tests) >= 2 else None
        failures_reduced = int(getattr(latest, "failures_reduced", 0))
        if previous is not None and failures_reduced == 0:
            failures_reduced = max(0, int(previous.failed_cases) - int(latest.failed_cases))

        no_new_failures = not bool(getattr(latest, "regression_detected", False))
        stable_pass_streak = int(getattr(latest, "stable_pass_streak", 1 if latest.passed else 0))

        stalled = False
        if len(tests) >= 2:
            newest = tests[-1]
            older = tests[-2]
            if (
                int(newest.failed_cases) >= int(older.failed_cases)
                and not newest.passed
                and not older.passed
            ):
                stalled = True

        return {
            "failures_reduced": failures_reduced,
            "no_new_failures": no_new_failures,
            "stable_pass_streak": stable_pass_streak,
            "stalled": stalled,
        }

    def start(self, backlog_item: BacklogItem) -> WorkflowState:
        state = WorkflowState(backlog_item_id=backlog_item.artifact_id)
        backlog_item.workflow_id = state.workflow_id
        backlog_item.stage = WorkflowStage.BACKLOG_INTAKE
        self.artifact_store.save(backlog_item)
        state.artifact_ids.append(backlog_item.artifact_id)
        self.state_store.save(state)

        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.WORKFLOW_STARTED,
            stage=state.current_stage,
            payload={"backlog_item_id": backlog_item.artifact_id},
        )
        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.ARTIFACT_CREATED,
            stage=state.current_stage,
            payload={
                "artifact_id": backlog_item.artifact_id,
                "artifact_type": backlog_item.__class__.__name__,
            },
        )
        return state

    def execute_next(self, workflow_id: str) -> WorkflowState:
        state = self.state_store.load(workflow_id)
        if state.status != WorkflowStatus.IN_PROGRESS:
            return state

        stage = state.current_stage
        self.event_bus.emit(workflow_id=state.workflow_id, event_type=EventType.STAGE_STARTED, stage=stage)

        role = STAGE_TO_ROLE.get(stage)
        if role is None:
            state.current_stage = WorkflowStage.DONE
            state.status = WorkflowStatus.COMPLETED
            self.state_store.save(state)
            return state

        agent = self.agents[role]
        context = AgentContext(workflow_state=state, artifacts=self.artifact_store.list_by_workflow(state.workflow_id))
        result = agent.act(context)

        for artifact in result.produced_artifacts:
            self.artifact_store.save(artifact)
            state.artifact_ids.append(artifact.artifact_id)
            if isinstance(artifact, PullRequest):
                state.pull_request_ids.append(artifact.artifact_id)
            if isinstance(artifact, ReviewFeedback):
                state.review_feedback_ids.append(artifact.artifact_id)
            self.event_bus.emit(
                workflow_id=state.workflow_id,
                event_type=EventType.ARTIFACT_CREATED,
                stage=stage,
                payload={"artifact_id": artifact.artifact_id, "artifact_type": artifact.__class__.__name__},
            )

        if result.escalation_request is not None:
            escalation = self.escalation_service.raise_escalation(
                workflow_id=state.workflow_id,
                reason=result.escalation_request.reason,
                raised_by=result.escalation_request.raised_by,
            )
            state.escalation_ids.append(escalation.escalation_id)
            state.status = WorkflowStatus.ESCALATED
            self.event_bus.emit(
                workflow_id=state.workflow_id,
                event_type=EventType.ESCALATION_RAISED,
                stage=stage,
                payload={"escalation_id": escalation.escalation_id, "reason": escalation.reason},
            )

        if result.decision is not None:
            self.event_bus.emit(
                workflow_id=state.workflow_id,
                event_type=EventType.DECISION_MADE,
                stage=stage,
                payload={"decision": result.decision.value, "notes": result.notes},
            )

        if is_review_gate(stage) and result.decision is not None:
            approval = self.approval_service.create_approval(
                workflow_id=state.workflow_id,
                stage=stage,
                reviewer=role,
                decision=result.decision,
                comments=result.notes,
            )
            state.approval_ids.append(approval.approval_id)
            self.event_bus.emit(
                workflow_id=state.workflow_id,
                event_type=EventType.APPROVAL_RECORDED,
                stage=stage,
                payload={"approval_id": approval.approval_id, "decision": approval.decision.value},
            )

            if result.decision == Decision.REQUEST_CHANGES:
                progress = self._build_progress_summary(state.workflow_id)
                stalled = bool(progress.get("stalled", False))
                regression_detected = not bool(progress.get("no_new_failures", True))

                if stalled and state.revision >= 2:
                    escalation = self.escalation_service.raise_escalation(
                        workflow_id=state.workflow_id,
                        reason=(
                            "⛔ Workflow stalled: No progress in test failure reduction across two revision attempts. "
                            "The team has iterated twice without fixing any failing tests. "
                            "This requires human review and decision on how to proceed (redesign approach, escalate to specialist, etc.). "
                            f"Summary: {progress.get('failures_reduced', 0)} failures fixed, "
                            f"no new failures={progress.get('no_new_failures', True)}"
                        ),
                        raised_by="workflow_engine",
                    )
                    state.escalation_ids.append(escalation.escalation_id)
                    state.status = WorkflowStatus.ESCALATED
                    state.current_stage = WorkflowStage.DONE
                    self.event_bus.emit(
                        workflow_id=state.workflow_id,
                        event_type=EventType.ESCALATION_RAISED,
                        stage=stage,
                        payload={
                            "escalation_id": escalation.escalation_id,
                            "reason": escalation.reason,
                            "progress": progress,
                        },
                    )
                elif regression_detected and state.revision >= self.max_revisions - 1:
                    escalation = self.escalation_service.raise_escalation(
                        workflow_id=state.workflow_id,
                        reason=(
                            "⛔ Regression detected at revision limit: The latest iteration introduced NEW failing tests "
                            "and we're running out of revision attempts to fix it. "
                            "This needs human intervention to decide whether to pivot the approach or accept risk. "
                            f"Summary: {progress.get('failures_reduced', 0)} failures fixed in this revision, "
                            f"but new failures appeared"
                        ),
                        raised_by="workflow_engine",
                    )
                    state.escalation_ids.append(escalation.escalation_id)
                    state.status = WorkflowStatus.ESCALATED
                    state.current_stage = WorkflowStage.DONE
                    self.event_bus.emit(
                        workflow_id=state.workflow_id,
                        event_type=EventType.ESCALATION_RAISED,
                        stage=stage,
                        payload={
                            "escalation_id": escalation.escalation_id,
                            "reason": escalation.reason,
                            "progress": progress,
                        },
                    )
                else:
                    state.revision += 1
                    state.current_stage = WorkflowStage.IMPLEMENTATION
                    self.event_bus.emit(
                        workflow_id=state.workflow_id,
                        event_type=EventType.REVISION_STARTED,
                        stage=WorkflowStage.IMPLEMENTATION,
                        payload={
                            "old_revision": state.revision - 1,
                            "new_revision": state.revision,
                            "reason": "Revision loop triggered by REQUEST_CHANGES from previous gate",
                        },
                    )
            else:
                state.current_stage = default_next_stage(stage)
        else:
            state.current_stage = default_next_stage(stage)

        state.stage_history.append(stage)
        state.last_updated_at = datetime.now(timezone.utc)
        self.state_store.save(state)
        
        # Emit transition event for graph visualization
        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.TRANSITION_OCCURRED,
            stage=stage,
            payload={
                "from_stage": stage.value,
                "to_stage": state.current_stage.value,
                "revision": state.revision,
            },
        )
        
        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.STAGE_COMPLETED,
            stage=stage,
            payload={"stage_result": asdict(result)},
        )
        return state

    def run_until_terminal(self, workflow_id: str, max_steps: int = 100) -> WorkflowState:
        for _ in range(max_steps):
            state = self.state_store.load(workflow_id)
            if state.status != WorkflowStatus.IN_PROGRESS:
                return state
            # If we're at DONE stage but still IN_PROGRESS, process it once more to set COMPLETED status
            if state.current_stage == WorkflowStage.DONE:
                self.execute_next(workflow_id)
                return self.state_store.load(workflow_id)
            self.execute_next(workflow_id)
        return self.state_store.load(workflow_id)
