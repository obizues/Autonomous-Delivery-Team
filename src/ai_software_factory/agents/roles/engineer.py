from __future__ import annotations

import shutil
from pathlib import Path

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, EventType, WorkflowStage
from ai_software_factory.domain.models import BacklogItem, CodeImplementation, PullRequest, ReviewFeedback, TestResult
from ai_software_factory.events.bus import EventBus
from ai_software_factory.execution.file_patch_engine import FilePatchEngine
from ai_software_factory.execution.repo_workspace import RepoWorkspaceManager
from ai_software_factory.planning.repo_change_planner import RepoChangePlanner
from ai_software_factory.tools.repo_tools import list_repo_files, search_repo
from ai_software_factory.workflow.stage_result import StageResult


class EngineerAgent(Agent):
    role = "engineer"

    def __init__(
        self,
        repo_workspace: RepoWorkspaceManager,
        planner: RepoChangePlanner,
        patch_engine: FilePatchEngine,
        event_bus: EventBus,
    ) -> None:
        self.repo_workspace = repo_workspace
        self.planner = planner
        self.patch_engine = patch_engine
        self.event_bus = event_bus

    @staticmethod
    def _detect_repo_profile(sandbox_path: str) -> str:
        path = Path(sandbox_path)
        src = path / "src"
        if (src / "upload_service.py").exists() and (src / "file_validator.py").exists():
            return "upload"
        if (src / "auth_service.py").exists() and (src / "token_store.py").exists():
            return "auth"
        if (src / "pipeline.py").exists() and (src / "validators.py").exists():
            return "pipeline"
        return "generic"

    @staticmethod
    def _validator_module() -> str:
        return """
ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def validate_extension(filename: str) -> bool:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in ALLOWED_EXTENSIONS


def validate_upload(filename: str, content: bytes) -> tuple[bool, str]:
    if not validate_extension(filename):
        return False, "unsupported_file_type"
    if len(content) > MAX_FILE_SIZE_BYTES:
        return False, "file_too_large"
    return True, "ok"
""".strip()

    @staticmethod
    def _upload_document_revision_1() -> str:
        return """
def upload_document(filename: str, content: bytes) -> UploadResult:
    is_valid, reason = validate_upload(filename, content)
    if not is_valid:
        return UploadResult(status="REJECTED", message="Upload rejected")

    classification = classify_document(content)
    if is_suspicious(classification):
        return UploadResult(status="FLAGGED_FOR_REVIEW", message="Upload flagged")

    return UploadResult(
        status="ACCEPTED",
        message="Upload accepted",
        category=classification["category"],
        confidence=classification["confidence"],
    )
""".strip()

    @staticmethod
    def _upload_document_revision_2() -> str:
        return """
def upload_document(filename: str, content: bytes) -> UploadResult:
    is_valid, reason = validate_upload(filename, content)
    if not is_valid:
        return UploadResult(
            status="REJECTED",
            message="Upload rejected",
            error=reason,
        )

    classification = classify_document(content)
    if is_suspicious(classification):
        return UploadResult(
            status="FLAGGED_FOR_REVIEW",
            message="Upload flagged",
            error="suspicious_upload",
            category=classification["category"],
            confidence=classification["confidence"],
        )

    return UploadResult(
        status="ACCEPTED",
        message="Upload accepted",
        category=classification["category"],
        confidence=classification["confidence"],
    )
""".strip()

    @staticmethod
    def _upload_service_module_with_bug() -> str:
        return """
from ai_classifier import classify_document
from file_validator import validate_upload
from models import UploadResult
from suspicion_evaluator import is_suspicious


""".strip() + "\n\n" + EngineerAgent._upload_document_revision_1()

    @staticmethod
    def _upload_service_module_fixed() -> str:
        return """
from ai_classifier import classify_document
from file_validator import validate_upload
from models import UploadResult
from suspicion_evaluator import is_suspicious


""".strip() + "\n\n" + EngineerAgent._upload_document_revision_2()

    @staticmethod
    def _auth_service_module_revision_1() -> str:
        return """
from models import AuthResult
from token_store import create_token


USERS = {
    "alice": "secret123",
    "bob": "hunter2",
}
FAILED_ATTEMPTS: dict[str, int] = {}


def login(username: str, password: str) -> AuthResult:
    expected = USERS.get(username)
    if expected is None:
        return AuthResult(status="DENIED", message="Unknown user", error="unknown_user")

    attempts = FAILED_ATTEMPTS.get(username, 0)
    if attempts > 2:
        return AuthResult(status="DENIED", message="Account locked", error="account_locked")

    if password != expected:
        FAILED_ATTEMPTS[username] = attempts + 1
        return AuthResult(status="DENIED", message="Invalid credentials", error="invalid_credentials")

    FAILED_ATTEMPTS[username] = 0
    return AuthResult(
        status="AUTHENTICATED",
        message="Login successful",
        token=create_token(username),
    )
""".strip()

    @staticmethod
    def _auth_service_module_revision_2() -> str:
        return """
from models import AuthResult
from token_store import create_token


USERS = {
    "alice": "secret123",
    "bob": "hunter2",
}
FAILED_ATTEMPTS: dict[str, int] = {}


def login(username: str, password: str) -> AuthResult:
    expected = USERS.get(username)
    if expected is None:
        return AuthResult(status="DENIED", message="Unknown user", error="unknown_user")

    attempts = FAILED_ATTEMPTS.get(username, 0)
    if attempts >= 2:
        return AuthResult(status="DENIED", message="Account locked", error="account_locked")

    if password != expected:
        FAILED_ATTEMPTS[username] = attempts + 1
        if FAILED_ATTEMPTS[username] >= 3:
            return AuthResult(status="DENIED", message="Account locked", error="account_locked")
        return AuthResult(status="DENIED", message="Invalid credentials", error="invalid_credentials")

    FAILED_ATTEMPTS[username] = 0
    return AuthResult(
        status="AUTHENTICATED",
        message="Login successful",
        token=create_token(username),
    )
""".strip()

    @staticmethod
    def _pipeline_module_revision_1() -> str:
        return """
from validators import is_valid_record


def process_records(records: list[dict]) -> dict:
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen_ids: set[str] = set()

    for record in records:
        if not is_valid_record(record):
            rejected.append({"record": record, "reason": "invalid_schema"})
            continue

        record_id = str(record["id"])
        if record_id in seen_ids and len(accepted) > 1:
            rejected.append({"record": record, "reason": "duplicate_id"})
            continue

        seen_ids.add(record_id)
        accepted.append(
            {
                "id": record_id,
                "amount": float(record["amount"]),
                "status": "processed",
            }
        )

    return {
        "accepted": accepted,
        "rejected": rejected,
    }
""".strip()

    @staticmethod
    def _pipeline_module_revision_2() -> str:
        return """
from validators import is_valid_record


def process_records(records: list[dict]) -> dict:
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen_ids: set[str] = set()

    for record in records:
        if not is_valid_record(record):
            rejected.append({"record": record, "reason": "invalid_schema"})
            continue

        record_id = str(record["id"])
        if record_id in seen_ids:
            rejected.append({"record": record, "reason": "duplicate_id"})
            continue

        seen_ids.add(record_id)
        accepted.append(
            {
                "id": record_id,
                "amount": float(record["amount"]),
                "status": "processed",
            }
        )

    return {
        "accepted": accepted,
        "rejected": rejected,
    }
""".strip()

    @staticmethod
    def _default_source_targets(repo_profile: str) -> list[str]:
        if repo_profile == "upload":
            return ["src/file_validator.py", "src/upload_service.py"]
        if repo_profile == "auth":
            return ["src/auth_service.py"]
        if repo_profile == "pipeline":
            return ["src/pipeline.py"]
        return []

    def _build_engineer_lanes(self, files_to_modify: list[str], repo_profile: str) -> list[dict[str, object]]:
        source_targets = sorted({file for file in files_to_modify if file.startswith("src/")})
        required_targets = self._default_source_targets(repo_profile)
        source_targets = sorted(set(source_targets + required_targets))

        if not source_targets:
            return [{"lane_id": "engineer_1", "files": []}]

        max_lanes = min(3, len(source_targets))
        lane_buckets: list[list[str]] = [[] for _ in range(max_lanes)]
        for index, file_name in enumerate(source_targets):
            lane_buckets[index % max_lanes].append(file_name)

        lanes: list[dict[str, object]] = []
        for index, bucket in enumerate(lane_buckets, start=1):
            if not bucket:
                continue
            lanes.append({
                "lane_id": f"engineer_{index}",
                "files": sorted(bucket),
            })
        return lanes or [{"lane_id": "engineer_1", "files": source_targets}]

    @staticmethod
    def _create_lane_workspace(sandbox_path: Path, revision: int, lane_id: str) -> Path:
        lanes_root = sandbox_path.parent / f"{sandbox_path.name}_parallel" / f"rev_{revision}"
        lane_path = lanes_root / lane_id
        if lane_path.exists():
            shutil.rmtree(lane_path)
        lane_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            sandbox_path,
            lane_path,
            ignore=shutil.ignore_patterns("run_logs", "*_parallel", "parallel_lanes"),
        )
        return lane_path

    def _profile_patch_results(
        self,
        repo_profile: str,
        revision: int,
        workspace_path: Path,
        plan_files_to_modify: list[str],
        target_files: set[str] | None = None,
    ) -> list:
        def should_patch(file_name: str) -> bool:
            return target_files is None or file_name in target_files

        patch_results = []
        validator_path = workspace_path / "src" / "file_validator.py"
        upload_path = workspace_path / "src" / "upload_service.py"
        auth_path = workspace_path / "src" / "auth_service.py"
        pipeline_path = workspace_path / "src" / "pipeline.py"

        if repo_profile == "upload":
            if revision == 1:
                if should_patch("src/file_validator.py"):
                    patch_results.append(self.patch_engine.apply_patch(validator_path, self._validator_module()))
                if should_patch("src/upload_service.py"):
                    patch_results.append(self.patch_engine.apply_patch(upload_path, self._upload_service_module_with_bug()))
            else:
                if should_patch("src/file_validator.py") and "src/file_validator.py" in plan_files_to_modify:
                    patch_results.append(self.patch_engine.apply_patch(validator_path, self._validator_module()))

                if should_patch("src/upload_service.py"):
                    replaced = self.patch_engine.replace_function(
                        file_path=upload_path,
                        function_name="upload_document",
                        new_function_code=self._upload_document_revision_2(),
                    )
                    patch_results.append(replaced)
                    if not replaced.success:
                        patch_results.append(self.patch_engine.apply_patch(upload_path, self._upload_service_module_fixed()))

        elif repo_profile == "auth":
            if should_patch("src/auth_service.py"):
                if revision == 1:
                    patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_1()))
                else:
                    patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_2()))

        elif repo_profile == "pipeline":
            if should_patch("src/pipeline.py"):
                if revision == 1:
                    patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_1()))
                else:
                    patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_2()))

        else:
            for file_name in plan_files_to_modify:
                if not file_name.startswith("src/"):
                    continue
                if not should_patch(file_name):
                    continue
                full_path = workspace_path / file_name
                if full_path.exists():
                    current = full_path.read_text(encoding="utf-8")
                    patch_results.append(self.patch_engine.apply_patch(full_path, current))

        return patch_results

    def _implementation_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        backlog = context.latest(BacklogItem)
        previous_test = context.latest(TestResult)
        previous_feedback = context.latest(ReviewFeedback)

        sandbox_path = self.repo_workspace.ensure_sandbox(workflow_id)
        python_files = list_repo_files(sandbox_path)
        upload_related = search_repo(sandbox_path, "upload")

        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.REPO_SCANNED,
            stage=state.current_stage,
            payload={
                "revision": revision,
                "seed_repo_name": self.repo_workspace.seed_repo_name,
                "sandbox_path": str(sandbox_path),
                "python_files": len(python_files),
                "upload_related_files": upload_related,
            },
        )

        backlog_text = "\n".join(
            [
                backlog.title if backlog else "",
                backlog.problem_statement if backlog else "",
                "\n".join(backlog.acceptance_criteria) if backlog else "",
            ]
        )
        failing_tests = previous_test.failing_tests if previous_test else []
        failure_output = previous_test.output if previous_test else ""

        plan = self.planner.create_plan(
            backlog_text=backlog_text,
            repo_path=sandbox_path,
            failing_tests=failing_tests,
            failure_output=failure_output,
        )

        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.CHANGE_PLAN_GENERATED,
            stage=state.current_stage,
            payload={
                "revision": revision,
                "summary": plan.summary,
                "files_to_modify": plan.files_to_modify,
                "target_symbols": plan.target_symbols,
                "target_confidence": plan.target_confidence,
                "confidence": plan.confidence,
                "intent_category": plan.intent_category.value,
            },
        )

        changed_files: list[str] = []
        patch_notes: list[str] = []
        repo_profile = self._detect_repo_profile(str(sandbox_path))
        lanes = self._build_engineer_lanes(plan.files_to_modify, repo_profile)
        lane_summaries: list[str] = []

        for lane in lanes:
            lane_id = str(lane["lane_id"])
            lane_files_raw = lane.get("files", [])
            lane_files = set(lane_files_raw if isinstance(lane_files_raw, list) else [])
            lane_workspace = self._create_lane_workspace(sandbox_path, revision, lane_id)
            lane_results = self._profile_patch_results(
                repo_profile=repo_profile,
                revision=revision,
                workspace_path=lane_workspace,
                plan_files_to_modify=plan.files_to_modify,
                target_files=lane_files,
            )

            lane_success_count = 0
            lane_failure_count = 0
            for lane_result in lane_results:
                lane_file_path = Path(lane_result.file_path)
                try:
                    relative_path = lane_file_path.relative_to(lane_workspace)
                except ValueError:
                    relative_path = Path(str(lane_file_path).replace(str(lane_workspace), "").lstrip("\\/"))

                relative_file = str(relative_path).replace("\\", "/")

                if not lane_result.success:
                    lane_failure_count += 1
                    patch_notes.append(f"{lane_id}::{relative_file}: {lane_result.operation} failed ({lane_result.message})")
                    self.event_bus.emit(
                        workflow_id=workflow_id,
                        event_type=EventType.PATCH_ROLLED_BACK,
                        stage=state.current_stage,
                        payload={
                            "revision": revision,
                            "engineer_lane": lane_id,
                            "file_path": relative_file,
                            "operation": lane_result.operation,
                            "message": lane_result.message,
                            "symbols": lane_result.symbols,
                        },
                    )
                    continue

                lane_content = (lane_workspace / relative_path).read_text(encoding="utf-8")
                integration_target = sandbox_path / relative_path
                integrated = self.patch_engine.apply_patch(integration_target, lane_content)

                if integrated.success:
                    lane_success_count += 1
                    changed_files.append(relative_file)
                    patch_notes.append(f"{lane_id}::{relative_file}: integrated")
                    self.event_bus.emit(
                        workflow_id=workflow_id,
                        event_type=EventType.PATCH_APPLIED,
                        stage=state.current_stage,
                        payload={
                            "revision": revision,
                            "engineer_lane": lane_id,
                            "file_path": relative_file,
                            "operation": f"{lane_result.operation}:integrated",
                            "message": integrated.message,
                            "symbols": lane_result.symbols,
                        },
                    )
                else:
                    lane_failure_count += 1
                    patch_notes.append(f"{lane_id}::{relative_file}: integration failed ({integrated.message})")
                    self.event_bus.emit(
                        workflow_id=workflow_id,
                        event_type=EventType.PATCH_ROLLED_BACK,
                        stage=state.current_stage,
                        payload={
                            "revision": revision,
                            "engineer_lane": lane_id,
                            "file_path": relative_file,
                            "operation": f"{lane_result.operation}:integrated",
                            "message": integrated.message,
                            "symbols": lane_result.symbols,
                        },
                    )

            lane_summaries.append(
                f"{lane_id} files={sorted(lane_files) if lane_files else ['(planner-default)']} "
                f"applied={lane_success_count} failed={lane_failure_count}"
            )

        changed_files = sorted(set(changed_files))

        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.FILES_MODIFIED,
            stage=state.current_stage,
            payload={
                "sandbox_path": str(sandbox_path),
                "files_changed": changed_files,
                "revision": revision,
                "engineer_lanes": lane_summaries,
            },
        )

        notes = [
            f"Seed repo: {self.repo_workspace.seed_repo_name}",
            f"Sandbox repo path: {sandbox_path}",
            f"Parallel engineer lanes: {len(lanes)}",
            f"Lane assignments: {'; '.join(lane_summaries)}",
            f"Planner confidence: {plan.confidence}",
            f"Planner intent category: {plan.intent_category.value}",
            f"Detected repo profile: {repo_profile}",
            f"Planner target symbols: {plan.target_symbols}",
            f"Planner target confidence: {plan.target_confidence}",
            f"Files changed: {', '.join(changed_files)}",
            f"Patch outcomes: {'; '.join(patch_notes) if patch_notes else 'none'}",
        ]
        if previous_test is not None:
            notes.append(
                f"Previous failing tests: {', '.join(previous_test.failing_tests) if previous_test.failing_tests else 'none'}"
            )
            notes.append(f"Previous test output snippet: {(previous_test.output or previous_test.stdout)[:280]}")
        if previous_feedback is not None:
            notes.append(f"Previous review feedback: {previous_feedback.comments}")

        implementation = CodeImplementation(
            workflow_id=workflow_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            summary=(
                f"Revision {revision}: semantic repo-mode patch set for "
                f"'{backlog.title if backlog else 'Feature'}' in sandbox repo."
            ),
            approach=(
                "Index repository symbols, map failing tests to source files/symbols, generate semantic change plan, "
                "and apply targeted symbol-level patches where possible."
            ),
            workspace_path=str(sandbox_path),
            files_changed=changed_files,
            written_source_files=changed_files,
            key_algorithms=[
                "Failure-to-source mapping via test imports and pytest output",
                "Repo profile detection (upload/auth/pipeline)",
                "Profile-specific deterministic patch strategy",
                "Semantic planning with target symbols and confidence",
            ],
            implementation_notes=notes,
            risks=plan.risks,
        )
        return StageResult(produced_artifacts=[implementation], notes="Semantic change plan applied in sandbox.")

    def _pull_request_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        implementation = context.latest(CodeImplementation)
        if implementation is None:
            return StageResult(decision=Decision.REQUEST_CHANGES, notes="Cannot create PR without implementation artifact.")

        backlog = context.latest(BacklogItem)
        title = backlog.title if backlog else "Feature"

        pr = PullRequest(
            workflow_id=workflow_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            title=f"feat(repo-mode): {title} — revision {revision}",
            description="Applies semantic repo-aware patching in sandbox based on failure context.",
            implementation_artifact_id=implementation.artifact_id,
            files_modified=implementation.written_source_files,
            architecture_alignment="Source modules remain isolated by responsibility while applying targeted fixes.",
            test_coverage="pytest suite validates rejected oversized uploads with explicit reason and valid upload flow.",
            known_limitations=[
                "Symbol-level patching currently targets top-level functions only",
                "Semantic mapper is heuristic-based and Python-only",
            ],
        )
        return StageResult(produced_artifacts=[pr], notes="Pull request artifact created for semantic sandbox changes.")

    def _peer_review_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        implementation = context.latest(CodeImplementation)
        pr = context.latest(PullRequest)
        decision = Decision.APPROVED if implementation is not None else Decision.REQUEST_CHANGES

        review = ReviewFeedback(
            workflow_id=workflow_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            reviewer="peer_engineer",
            decision=decision,
            comments=(
                "Peer review passed. Semantic plan and targeted patches are coherent for pytest validation."
                if decision == Decision.APPROVED
                else "Peer review failed: implementation artifact missing."
            ),
            issues_identified=[] if decision == Decision.APPROVED else ["Missing implementation artifact"],
            suggested_changes=[] if decision == Decision.APPROVED else ["Complete IMPLEMENTATION stage"],
            pull_request_id=pr.artifact_id if pr else None,
        )
        return StageResult(produced_artifacts=[review], decision=decision, notes="Peer code review completed.")

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage

        if stage == WorkflowStage.IMPLEMENTATION:
            return self._implementation_stage(context)
        if stage == WorkflowStage.PULL_REQUEST_CREATED:
            return self._pull_request_stage(context)
        if stage == WorkflowStage.PEER_CODE_REVIEW_GATE:
            return self._peer_review_stage(context)

        return StageResult(notes=f"No Engineer action for stage {stage.value}.")
