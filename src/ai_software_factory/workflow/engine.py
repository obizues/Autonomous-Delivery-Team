from dataclasses import asdict
from datetime import datetime, timezone

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, EscalationStatus, EventType, WorkflowStage, WorkflowStatus
from ai_software_factory.domain.models import (
    BacklogItem,
    EscalationArtifact,
    HumanIntervention,
    PullRequest,
    ReviewFeedback,
    TestResult,
)
from ai_software_factory.events.bus import EventBus
from ai_software_factory.governance.approvals import ApprovalService
from ai_software_factory.governance.escalations import EscalationService
from ai_software_factory.persistence.artifact_store import ArtifactStore
from ai_software_factory.persistence.state_store import StateStore
from ai_software_factory.workflow.state import WorkflowState
from ai_software_factory.workflow.transitions import STAGE_TO_ROLE, default_next_stage, is_review_gate

class WorkflowEngine:
    def __init__(
        self,
        state_store: StateStore,
        artifact_store: ArtifactStore,
        event_bus: EventBus,
        agents: dict[str, Agent],
        approval_service: ApprovalService,
        escalation_service: EscalationService,
        max_revisions: int = 3,
        policy_manager=None,
        repo_paths: list[str] = [],
        multi_repo_coordinator=None,
        repo_ingestion_service=None,
    ) -> None:
        self.state_store = state_store
        self.artifact_store = artifact_store
        self.event_bus = event_bus
        self.agents = agents
        self.approval_service = approval_service
        self.escalation_service = escalation_service
        self.max_revisions = max_revisions
        from ai_software_factory.governance.policy import PolicyManager
        self.policy_manager = policy_manager or PolicyManager()
        self.repo_paths = repo_paths or []
        from ai_software_factory.orchestration.multi_repo import MultiRepoCoordinator
        self.multi_repo_coordinator = multi_repo_coordinator or MultiRepoCoordinator()
        from ai_software_factory.orchestration.repo_ingestion import RepoIngestionService
        self.repo_ingestion_service = repo_ingestion_service or RepoIngestionService()

    def link_and_validate_cross_repo_artifacts(self, workflow_id: str) -> None:
        """Automate linking and validation of artifacts across repo boundaries."""
        state = self.state_store.load(workflow_id)
        profiles = self.repo_ingestion_service.link_capability_reports()
        linked_artifacts = set()
        for profile in profiles:
            for artifact_id in profile.get("linked_artifacts", []):
                linked_artifacts.add(artifact_id)
        # Validate that each artifact is linked to at least one repo profile
        validation_results = {}
        for artifact_id in state.artifact_ids:
            validation_results[artifact_id] = artifact_id in linked_artifacts
        # Optionally emit validation event
        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type="CROSS_REPO_ARTIFACT_VALIDATED",
            stage=state.current_stage,
            payload={"validation_results": validation_results},
        )

    def coordinate_cross_repo_artifacts(self, workflow_id: str) -> None:
        """Coordinate delivery and artifact flow across repository boundaries."""
        state = self.state_store.load(workflow_id)
        profiles = self.repo_ingestion_service.link_capability_reports()
        for artifact_id in state.artifact_ids:
            artifact = self.artifact_store.load(artifact_id)
            # Find repo profile(s) matching artifact type or capability
            for profile in profiles:
                if artifact.__class__.__name__ in profile.get("artifact_types", []):
                    # Link artifact to repo profile for orchestration
                    if "linked_artifacts" not in profile:
                        profile["linked_artifacts"] = []
                    profile["linked_artifacts"].append(artifact_id)
        # Optionally emit orchestration event
        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type="CROSS_REPO_ARTIFACT_COORDINATED",
            stage=state.current_stage,
            payload={"profiles": profiles, "artifact_ids": state.artifact_ids},
        )

class WorkflowEngine:
    def __init__(
        self,
        state_store: StateStore,
        artifact_store: ArtifactStore,
        event_bus: EventBus,
        agents: dict[str, Agent],
        approval_service: ApprovalService,
        escalation_service: EscalationService,
        max_revisions: int = 3,
        policy_manager=None,
        repo_paths: list[str] = [],
        multi_repo_coordinator=None,
        repo_ingestion_service=None,
    ) -> None:
        self.state_store = state_store
        self.artifact_store = artifact_store
        self.event_bus = event_bus
        self.agents = agents
        self.approval_service = approval_service
        self.escalation_service = escalation_service
        self.max_revisions = max_revisions
        from ai_software_factory.governance.policy import PolicyManager
        self.policy_manager = policy_manager or PolicyManager()
        self.repo_paths = repo_paths or []
        from ai_software_factory.orchestration.multi_repo import MultiRepoCoordinator
        self.multi_repo_coordinator = multi_repo_coordinator or MultiRepoCoordinator()
        from ai_software_factory.orchestration.repo_ingestion import RepoIngestionService
        self.repo_ingestion_service = repo_ingestion_service or RepoIngestionService()

    def ingest_and_profile_repositories(self, repo_configs):
        """Ingest and profile repositories, updating orchestration state."""
        self.repo_ingestion_service.ingest_repositories(repo_configs)
        profiles = self.repo_ingestion_service.profile_repositories()
        self.multi_repo_coordinator.repo_profiles = profiles
        return profiles
    def select_repo_for_task(self, task_description):
        # Use agentic repo selection
        return self.multi_repo_coordinator.select_best_repo(task_description, required_capabilities=[])

    def start(self, backlog_item):
        """
        Start a new workflow for the given backlog item and return the initial WorkflowState.
        Automate backlog intake, prioritization, and assignment.
        """
        from ai_software_factory.workflow.state import WorkflowState
        from ai_software_factory.domain.enums import WorkflowStatus, WorkflowStage
        import uuid
        # Prioritize backlog item (simple: by business value or criteria count)
        priority = getattr(backlog_item, "business_value", "")
        if hasattr(backlog_item, "acceptance_criteria"):
            priority_score = len(backlog_item.acceptance_criteria)
        else:
            priority_score = 1
        # Assign to agent (simple: product_owner or engineer)
        assigned_agent = "engineer" if priority_score > 2 else "product_owner"
        workflow_id = str(uuid.uuid4())
        state = WorkflowState(
            backlog_item_id=backlog_item.artifact_id,
            workflow_id=workflow_id,
            current_stage=WorkflowStage.BACKLOG_INTAKE,
            status=WorkflowStatus.IN_PROGRESS,
            revision=1,
            artifact_ids=[backlog_item.artifact_id],
            stage_history=[],
            last_updated_at=datetime.now(timezone.utc),
        )
        self.state_store.save(state)
        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.WORKFLOW_STARTED,
            stage=WorkflowStage.BACKLOG_INTAKE,
            payload={"backlog_item_id": backlog_item.artifact_id, "priority": priority, "assigned_agent": assigned_agent},
        )
        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.ARTIFACT_CREATED,
            stage=WorkflowStage.BACKLOG_INTAKE,
            payload={
                "artifact_id": backlog_item.artifact_id,
                "artifact_type": backlog_item.__class__.__name__,
                "priority": priority,
                "assigned_agent": assigned_agent,
            },
        )
        return state

    def _record_escalation(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
        reason: str,
        raised_by: str,
        extra_payload: dict[str, object] | None = None,
    ) -> EscalationArtifact:
        self.escalation_service.raise_escalation(
            workflow_id=state.workflow_id,
            reason=reason,
            raised_by=raised_by,
        )
        escalation = EscalationArtifact(
            workflow_id=state.workflow_id,
            stage=stage,
            created_by=raised_by,
            version=state.revision,
            status=ArtifactStatus.FINAL,
            reason=reason,
            raised_by=raised_by,
        )
        self.artifact_store.save(escalation)
        state.artifact_ids.append(escalation.artifact_id)
        state.escalation_ids.append(escalation.artifact_id)
        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.ARTIFACT_CREATED,
            stage=stage,
            payload={"artifact_id": escalation.artifact_id, "artifact_type": escalation.__class__.__name__},
        )
        self.event_bus.emit(
            workflow_id=state.workflow_id,
            event_type=EventType.ESCALATION_RAISED,
            stage=stage,
            payload={
                "escalation_id": escalation.artifact_id,
                "reason": escalation.reason,
                **(extra_payload or {}),
            },
        )
        return escalation

    def latest_escalation(self, workflow_id: str) -> EscalationArtifact | None:
        artifacts = self.artifact_store.list_by_workflow(workflow_id)
        escalations = [artifact for artifact in artifacts if isinstance(artifact, EscalationArtifact)]
        return escalations[-1] if escalations else None

    def _latest_gate_feedback_decisions(self, workflow_id: str) -> dict[WorkflowStage, Decision]:
        artifacts = self.artifact_store.list_by_workflow(workflow_id)
        latest: dict[WorkflowStage, tuple[int, Decision]] = {}
        for artifact in artifacts:
            if not isinstance(artifact, ReviewFeedback):
                continue
            if not is_review_gate(artifact.stage):
                continue
            existing = latest.get(artifact.stage)
            if existing is None or artifact.version >= existing[0]:
                latest[artifact.stage] = (artifact.version, artifact.decision)
        return {stage: payload[1] for stage, payload in latest.items()}

    def resume_from_escalation(
        self,
        workflow_id: str,
        human_response: str,
        responder: str = "human_operator",
        resume_stage: WorkflowStage | None = None,
        response_template: str = "",
        resume_max_steps: int = 120,
    ) -> WorkflowState:
        state = self.state_store.load(workflow_id)
        if state.status != "ESCALATED":
            raise ValueError(f"Workflow {workflow_id} is not escalated.")
        # Find escalation artifact for any stage
        escalation = None
        for artifact in self.artifact_store.list_by_workflow(workflow_id):
            if isinstance(artifact, EscalationArtifact) and getattr(artifact, "stage", None) == (resume_stage or state.current_stage):
                escalation = artifact
                break
        if escalation is None:
            raise ValueError(f"Workflow {workflow_id} has no escalation artifact to resolve at stage {(resume_stage or state.current_stage)}.")
        escalation.human_response = human_response
        escalation.escalation_status = EscalationStatus.RESOLVED
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolution_summary = f"Human response recorded. Resume from {resume_stage.value if resume_stage else state.current_stage}."
        self.artifact_store.save(escalation)
        state.status = WorkflowStatus.IN_PROGRESS
        if resume_stage:
            state.current_stage = resume_stage
        self.state_store.save(state)
        return state

    def execute_next(self, workflow_id: str) -> WorkflowState | None:
        state = self.state_store.load(workflow_id)
        if state is None:
            return None
        if state.status != WorkflowStatus.IN_PROGRESS:
            return state
        stage = state.current_stage
        self.event_bus.emit(workflow_id=state.workflow_id, event_type=EventType.STAGE_STARTED, stage=stage)

        # Handle resume from escalation for any stage
        if state.status == WorkflowStatus.ESCALATED:
            # If human intervention artifact exists, resume workflow
            escalation_artifacts = [a for a in self.artifact_store.list_by_workflow(state.workflow_id) if getattr(a, "stage", None) == state.current_stage and getattr(a, "escalation_status", None) == "RESOLVED"]
            if escalation_artifacts:
                state.status = WorkflowStatus.IN_PROGRESS
                self.state_store.save(state)
            else:
                return state
        if state.status != WorkflowStatus.IN_PROGRESS:
            return state

        # Policy-driven escalation checks for all stages
        gate_policy = self.policy_manager.get_gate_policy(str(stage))
        min_artifacts = gate_policy.get("min_artifacts")
        if min_artifacts is not None:
            artifacts = self.artifact_store.list_by_workflow(state.workflow_id)
            if len(artifacts) < min_artifacts:
                self._record_escalation(
                    state=state,
                    stage=stage,
                    reason=f"Minimum artifacts ({min_artifacts}) not met for stage {stage}.",
                    raised_by="policy_manager",
                    extra_payload={"min_artifacts": min_artifacts, "actual": len(artifacts)}
                )
                state.status = WorkflowStatus.ESCALATED
                self.state_store.save(state)
                return state

        revision_budget = self.policy_manager.get_revision_budget()
        if state.revision > revision_budget:
            self._record_escalation(
                state=state,
                stage=stage,
                reason=f"Revision budget ({revision_budget}) exceeded at stage {stage}.",
                raised_by="policy_manager",
                extra_payload={"revision": state.revision, "budget": revision_budget}
            )
            state.status = WorkflowStatus.ESCALATED
            self.state_store.save(state)
            return state

        role = STAGE_TO_ROLE.get(stage)
        if role is None:
            latest_gate_decisions = self._latest_gate_feedback_decisions(state.workflow_id)
            unresolved_gates = [
                gate.value
                for gate, decision in latest_gate_decisions.items()
                if decision == Decision.REQUEST_CHANGES
            ]
            if unresolved_gates:
                self._record_escalation(
                    state=state,
                    stage=stage,
                    reason=(
                        "⛔ Completion blocked: latest gate decision still requests changes for "
                        + ", ".join(sorted(unresolved_gates))
                        + ". Workflow cannot enter DONE until all latest gate decisions are APPROVED."
                    ),
                    raised_by="workflow_engine",
                    extra_payload={"unresolved_gates": unresolved_gates},
                )
                state.current_stage = WorkflowStage.DONE
                state.status = WorkflowStatus.ESCALATED
                self.state_store.save(state)
                return state

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
            escalation = self._record_escalation(
                state=state,
                stage=stage,
                reason=result.escalation_request.reason,
                raised_by=result.escalation_request.raised_by,
            )
            state.status = WorkflowStatus.ESCALATED
            self.state_store.save(state)
            return state

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

                if state.revision >= self.max_revisions:
                    escalation = self._record_escalation(
                        state=state,
                        stage=stage,
                        reason=(
                            "⛔ Revision budget exhausted: review gates requested changes at or beyond the configured "
                            f"revision limit ({self.max_revisions}). Human decision required to continue."
                        ),
                        raised_by="workflow_engine",
                        extra_payload={"progress": progress, "max_revisions": self.max_revisions},
                    )
                    state.status = WorkflowStatus.ESCALATED
                    state.current_stage = WorkflowStage.DONE
                elif stalled and state.revision >= 2:
                    escalation = self._record_escalation(
                        state=state,
                        stage=stage,
                        reason=(
                            "⛔ Workflow stalled: No progress in test failure reduction across two revision attempts. "
                            "The team has iterated twice without fixing any failing tests. "
                            "This requires human review and decision on how to proceed (redesign approach, escalate to specialist, etc.). "
                            f"Summary: {progress.get('failures_reduced', 0)} failures fixed, "
                            f"no new failures={progress.get('no_new_failures', True)}"
                        ),
                        raised_by="workflow_engine",
                        extra_payload={"progress": progress},
                    )
                    state.status = WorkflowStatus.ESCALATED
                    state.current_stage = WorkflowStage.DONE
                elif regression_detected and state.revision >= self.max_revisions - 1:
                    escalation = self._record_escalation(
                        state=state,
                        stage=stage,
                        reason=(
                            "⛔ Regression detected at revision limit: The latest iteration introduced NEW failing tests "
                            "and we're running out of revision attempts to fix it. "
                            "This needs human intervention to decide whether to pivot the approach or accept risk. "
                            f"Summary: {progress.get('failures_reduced', 0)} failures fixed in this revision, "
                            f"but new failures appeared"
                        ),
                        raised_by="workflow_engine",
                        extra_payload={"progress": progress},
                    )
                    state.status = WorkflowStatus.ESCALATED
                    state.current_stage = WorkflowStage.DONE
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

    def _build_progress_summary(self, workflow_id: str) -> dict:
        tests = []
        if hasattr(self.artifact_store, 'list_by_workflow'):
            tests = [artifact for artifact in self.artifact_store.list_by_workflow(workflow_id) if hasattr(artifact, 'failed_cases')]
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
            failures_reduced = max(0, int(getattr(previous, "failed_cases", 0)) - int(getattr(latest, "failed_cases", 0)))
        no_new_failures = not bool(getattr(latest, "regression_detected", False))
        stable_pass_streak = int(getattr(latest, "stable_pass_streak", 1 if getattr(latest, "passed", False) else 0))
        stalled = False
        if len(tests) >= 2:
            newest = tests[-1]
            older = tests[-2]
            if (
                int(getattr(newest, "failed_cases", 0)) >= int(getattr(older, "failed_cases", 0))
                and not getattr(newest, "passed", False)
                and not getattr(older, "passed", False)
            ):
                stalled = True
        return {
            "failures_reduced": failures_reduced,
            "no_new_failures": no_new_failures,
            "stable_pass_streak": stable_pass_streak,
            "stalled": stalled,
        }

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

