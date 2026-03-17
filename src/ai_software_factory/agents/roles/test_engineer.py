from __future__ import annotations

from pathlib import Path

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, EventType
from ai_software_factory.domain.models import CodeImplementation, PullRequest, ReviewFeedback, TestResult
from ai_software_factory.events.bus import EventBus
from ai_software_factory.execution.file_patch_engine import FilePatchEngine
from ai_software_factory.execution.test_runner import PytestRunner
from ai_software_factory.workflow.stage_result import StageResult


class TestEngineerAgent(Agent):
    role = "test_engineer"

    def __init__(
        self,
        patch_engine: FilePatchEngine,
        test_runner: PytestRunner,
        event_bus: EventBus,
    ) -> None:
        self.patch_engine = patch_engine
        self.test_runner = test_runner
        self.event_bus = event_bus

    @staticmethod
    def _test_file_validator_content() -> str:
        return """
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from file_validator import MAX_FILE_SIZE_BYTES, validate_upload


def test_supported_file_type_validation():
    is_valid, reason = validate_upload("file.pdf", b"hello")
    assert is_valid is True
    assert reason == "ok"


def test_unsupported_file_type_rejection():
    is_valid, reason = validate_upload("malware.exe", b"payload")
    assert is_valid is False
    assert reason == "unsupported_file_type"


def test_oversized_file_rejection():
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    is_valid, reason = validate_upload("large.pdf", oversized)
    assert is_valid is False
    assert reason == "file_too_large"
""".strip()

    @staticmethod
    def _test_upload_service_content() -> str:
        return """
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from file_validator import MAX_FILE_SIZE_BYTES
from upload_service import upload_document


def test_rejected_payload_includes_reason_for_oversized_files():
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    result = upload_document("large.pdf", oversized)
    assert result.status == "REJECTED"
    assert result.error == "file_too_large"


def test_valid_files_continue_to_upload():
    result = upload_document("valid.pdf", b"invoice payload")
    assert result.status in {"ACCEPTED", "FLAGGED_FOR_REVIEW"}
""".strip()

    @staticmethod
    def _test_auth_service_content() -> str:
        return """
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from auth_service import FAILED_ATTEMPTS, login


def test_invalid_password_denied():
    FAILED_ATTEMPTS.clear()
    result = login("alice", "wrong")
    assert result.status == "DENIED"
    assert result.error == "invalid_credentials"


def test_account_locks_after_three_failed_attempts():
    FAILED_ATTEMPTS.clear()
    login("alice", "wrong")
    login("alice", "wrong")
    result = login("alice", "wrong")
    assert result.status == "DENIED"
    assert result.error == "account_locked"


def test_valid_login_still_works():
    FAILED_ATTEMPTS.clear()
    result = login("alice", "secret123")
    assert result.status == "AUTHENTICATED"
    assert result.token == "token:alice"
""".strip()

    @staticmethod
    def _test_pipeline_content() -> str:
        return """
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from pipeline import process_records


def test_duplicate_ids_are_rejected_with_reason():
    result = process_records([
        {"id": "a1", "amount": "12.5"},
        {"id": "a1", "amount": "7.0"},
    ])
    assert len(result["accepted"]) == 1
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["reason"] == "duplicate_id"


def test_invalid_records_include_reason():
    result = process_records([
        {"id": "a1", "amount": "12.5"},
        {"amount": "7"},
    ])
    assert len(result["accepted"]) == 1
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["reason"] == "invalid_schema"
""".strip()

    @staticmethod
    def _detect_repo_profile(sandbox_path: str) -> str:
        root = Path(sandbox_path)
        src = root / "src"
        if (src / "upload_service.py").exists() and (src / "file_validator.py").exists():
            return "upload"
        if (src / "auth_service.py").exists() and (src / "token_store.py").exists():
            return "auth"
        if (src / "pipeline.py").exists() and (src / "validators.py").exists():
            return "pipeline"
        return "generic"

    def act(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        wf_id = state.workflow_id
        revision = state.revision

        implementation = context.latest(CodeImplementation)
        pr = context.latest(PullRequest)
        previous_result = context.latest(TestResult)
        if implementation is None or not implementation.workspace_path:
            return StageResult(
                decision=Decision.REQUEST_CHANGES,
                notes="Implementation workspace path missing; cannot execute tests.",
            )

        sandbox_path = implementation.workspace_path
        repo_profile = self._detect_repo_profile(sandbox_path)

        if repo_profile == "upload":
            self.patch_engine.apply_patch(
                file_path=f"{sandbox_path}/tests/test_file_validator.py",
                new_content=self._test_file_validator_content(),
            )
            self.patch_engine.apply_patch(
                file_path=f"{sandbox_path}/tests/test_upload_service.py",
                new_content=self._test_upload_service_content(),
            )
            generated_test_files = [
                "tests/test_file_validator.py",
                "tests/test_upload_service.py",
            ]
            unit_tests = [
                "test_supported_file_type_validation",
                "test_unsupported_file_type_rejection",
                "test_oversized_file_rejection",
            ]
            integration_tests = [
                "test_rejected_payload_includes_reason_for_oversized_files",
                "test_valid_files_continue_to_upload",
            ]
            edge_case_coverage = [
                "oversized uploads rejected",
                "error payload includes reason for rejected oversized file",
                "valid files continue through upload flow",
            ]
        elif repo_profile == "auth":
            self.patch_engine.apply_patch(
                file_path=f"{sandbox_path}/tests/test_auth_service.py",
                new_content=self._test_auth_service_content(),
            )
            generated_test_files = ["tests/test_auth_service.py"]
            unit_tests = [
                "test_invalid_password_denied",
                "test_account_locks_after_three_failed_attempts",
            ]
            integration_tests = ["test_valid_login_still_works"]
            edge_case_coverage = [
                "failed login attempts are tracked",
                "account lockout is enforced",
                "successful login remains available for valid credentials",
            ]
        elif repo_profile == "pipeline":
            self.patch_engine.apply_patch(
                file_path=f"{sandbox_path}/tests/test_pipeline.py",
                new_content=self._test_pipeline_content(),
            )
            generated_test_files = ["tests/test_pipeline.py"]
            unit_tests = [
                "test_duplicate_ids_are_rejected_with_reason",
                "test_invalid_records_include_reason",
            ]
            integration_tests = []
            edge_case_coverage = [
                "duplicate records are rejected with explicit reason",
                "schema-invalid records are routed to rejected set",
            ]
        else:
            generated_test_files = []
            unit_tests = []
            integration_tests = []
            edge_case_coverage = ["no profile-specific tests generated"]

        self.event_bus.emit(
            workflow_id=wf_id,
            event_type=EventType.TEST_EXECUTION_STARTED,
            stage=state.current_stage,
            payload={
                "revision": revision,
                "sandbox_path": sandbox_path,
                "test_files": generated_test_files,
            },
        )

        baseline_failures = previous_result.failing_tests if previous_result else []
        targeted_tests = baseline_failures[:5]
        outcome = self.test_runner.run_repo_tests(
            sandbox_path,
            revision,
            targeted_tests=targeted_tests,
            baseline_failures=baseline_failures,
        )

        self.event_bus.emit(
            workflow_id=wf_id,
            event_type=EventType.TEST_EXECUTION_COMPLETED,
            stage=state.current_stage,
            payload={
                "revision": revision,
                "passed": outcome.passed,
                "exit_code": outcome.exit_code,
                "failing_tests": outcome.failed_tests,
                "new_failures": outcome.new_failures,
                "regression_detected": outcome.regression_detected,
                "log_path": outcome.log_path,
            },
        )
        self.event_bus.emit(
            workflow_id=wf_id,
            event_type=EventType.TEST_PASSED if outcome.passed else EventType.TEST_FAILED,
            stage=state.current_stage,
            payload={
                "revision": revision,
                "failing_tests": outcome.failed_tests,
            },
        )

        decision = Decision.APPROVED if outcome.passed else Decision.REQUEST_CHANGES
        previous_failed = len(baseline_failures)
        failures_reduced = max(0, previous_failed - len(outcome.failed_tests))
        stable_pass_streak = 1 if outcome.passed else 0
        if previous_result is not None and outcome.passed and previous_result.passed:
            stable_pass_streak = int(previous_result.stable_pass_streak) + 1

        test_result = TestResult(
            workflow_id=wf_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            passed=outcome.passed,
            total_cases=len(unit_tests) + len(integration_tests),
            failed_cases=len(outcome.failed_tests),
            failures_reduced=failures_reduced,
            no_new_failures=not outcome.regression_detected,
            stable_pass_streak=stable_pass_streak,
            regression_detected=outcome.regression_detected,
            new_failures=outcome.new_failures,
            targeted_tests=outcome.targeted_tests,
            targeted_command=outcome.targeted_command,
            targeted_exit_code=outcome.targeted_exit_code,
            workspace_path=sandbox_path,
            run_log_path=outcome.log_path,
            test_command=outcome.command,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            output=outcome.output,
            failing_tests=outcome.failed_tests,
            generated_test_files=generated_test_files,
            unit_tests=unit_tests,
            integration_tests=integration_tests,
            edge_case_coverage=edge_case_coverage,
            coverage_estimate=(
                "All sandbox pytest checks passed."
                if outcome.passed
                else f"Sandbox pytest failed with {len(outcome.failed_tests)} failing tests."
            ),
            details=[
                f"pytest exit code: {outcome.exit_code}",
                f"targeted pytest exit code: {outcome.targeted_exit_code if outcome.targeted_tests else 'N/A'}",
                f"new failures: {', '.join(outcome.new_failures) if outcome.new_failures else 'none'}",
                f"pytest log: {outcome.log_path}",
                "Tests executed inside sandbox repo copy.",
            ],
            pull_request_id=pr.artifact_id if pr else None,
        )

        review = ReviewFeedback(
            workflow_id=wf_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            reviewer=self.role,
            decision=decision,
            comments=(
                "Sandbox pytest passed. Change set satisfies acceptance criteria."
                if outcome.passed
                else "Sandbox pytest failed. Revision required to address failing tests."
            ),
            issues_identified=[] if outcome.passed else [f"{name} failed" for name in outcome.failed_tests] + (
                [f"New regression: {name}" for name in outcome.new_failures]
                if outcome.new_failures
                else []
            ),
            suggested_changes=[] if outcome.passed else [
                "Use failing pytest output for profile-targeted patching",
                f"Address failing tests for repo profile '{repo_profile}'",
            ],
            pull_request_id=pr.artifact_id if pr else None,
        )

        notes = "Test validation gate approved." if outcome.passed else "Test validation gate requested changes."
        return StageResult(produced_artifacts=[test_result, review], decision=decision, notes=notes)
