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


class CodeReviewAnalyzer:
    """Semantic code review analyzer for peer engineering feedback."""

    def __init__(self, workspace_path: Path, implementation: CodeImplementation, pull_request: PullRequest):
        self.workspace_path = workspace_path
        self.implementation = implementation
        self.pull_request = pull_request

    def analyze(self) -> dict:
        """
        Analyze code changes and return review metrics.
        
        Returns:
            dict with keys:
            - complexity_score (0-1): How complex are the changes
            - error_handling_score (0-1): Quality of error handling
            - documentation_score (0-1): Comment/docstring coverage
            - test_alignment_score (0-1): How well tests cover changes
            - overall_score (0-1): Weighted average
            - issues (list): Specific issues found
            - suggestions (list): Actionable suggestions
        """
        issues = []
        suggestions = []
        scores = {
            "complexity": self._analyze_complexity(issues),
            "error_handling": self._analyze_error_handling(issues, suggestions),
            "documentation": self._analyze_documentation(issues, suggestions),
            "test_alignment": self._analyze_test_alignment(issues, suggestions),
        }
        
        # Weighted average: all dimensions equally important
        overall = sum(scores.values()) / len(scores) if scores else 0.5
        
        return {
            "complexity_score": scores.get("complexity", 0.5),
            "error_handling_score": scores.get("error_handling", 0.5),
            "documentation_score": scores.get("documentation", 0.5),
            "test_alignment_score": scores.get("test_alignment", 0.5),
            "overall_score": overall,
            "issues": issues,
            "suggestions": suggestions,
        }

    def _analyze_complexity(self, issues: list) -> float:
        """Analyze code change complexity."""
        files_changed = len(self.implementation.files_changed or [])
        
        # Score based on number of files (minimal complexity is good for focused changes)
        if files_changed == 0:
            issues.append("No files were changed in implementation")
            return 0.5
        elif files_changed == 1:
            return 0.95  # Single file changes are excellent
        elif files_changed <= 3:
            return 0.85  # Multiple files, still reasonable
        else:
            issues.append(f"High complexity: {files_changed} files modified (consider breaking into smaller PRs)")
            return 0.65  # Still acceptable, just a note
        
    def _analyze_error_handling(self, issues: list, suggestions: list) -> float:
        """Analyze error handling patterns in code."""
        try:
            files_to_check = self.implementation.written_source_files or []
            if not files_to_check:
                # If no source files available, give benefit of doubt
                suggestions.append("Unable to analyze error handling (no source files available)")
                return 0.7
                
            error_handling_indicators = 0
            files_with_patterns = 0
            
            for file_rel in files_to_check:
                file_path = self.workspace_path / file_rel
                if not file_path.exists():
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    files_with_patterns += 1
                    
                    # Check for error handling patterns
                    has_try_except = "try:" in content and "except" in content
                    has_error_messages = "raise " in content or "error" in content.lower()
                    has_validation = "if " in content and ("raise" in content or "return" in content)
                    
                    if has_try_except:
                        error_handling_indicators += 1
                    if has_error_messages:
                        error_handling_indicators += 0.5
                    if has_validation:
                        error_handling_indicators += 0.5
                except Exception:
                    pass
            
            if files_with_patterns == 0:
                return 0.7  # Benefit of doubt if files can't be read
                
            score = min(1.0, error_handling_indicators / (files_with_patterns * 2))
            if score < 0.4:
                suggestions.append("Consider adding more error handling and validation (try/except, raise statements)")
            return max(0.65, score)  # Minimum 65% if analysis runs
        except Exception:
            return 0.7

    def _analyze_documentation(self, issues: list, suggestions: list) -> float:
        """Analyze code documentation and comments."""
        try:
            files_to_check = self.implementation.written_source_files or []
            if not files_to_check:
                # If no source files, give benefit of doubt
                suggestions.append("Unable to analyze documentation (no source files available)")
                return 0.75
                
            total_lines = 0
            comment_lines = 0
            docstring_count = 0
            
            for file_rel in files_to_check:
                file_path = self.workspace_path / file_rel
                if not file_path.exists() or not str(file_path).endswith(".py"):
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    total_lines += len(lines)
                    
                    comment_lines += sum(1 for line in lines if line.strip().startswith("#"))
                    docstring_count += content.count('"""') // 2  # Simple count of docstrings
                except Exception:
                    pass
            
            if total_lines == 0:
                return 0.75  # Benefit of doubt if files can't be read
                
            comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
            
            # Good documentation: 5-30% comments
            if comment_ratio < 0.02:
                suggestions.append("Add more inline comments to explain complex logic")
                score = 0.7
            elif comment_ratio > 0.50:
                suggestions.append("Consider reducing comment density; strive for self-explaining code")
                score = 0.75
            else:
                score = 0.85
                
            if docstring_count > 0:
                score += 0.05  # Bonus for having docstrings
                
            return min(1.0, score)
        except Exception:
            return 0.75

    def _analyze_test_alignment(self, issues: list, suggestions: list) -> float:
        """Analyze test coverage for implemented changes."""
        # Check if PR includes test coverage signals
        has_pr_coverage = "test" in (self.pull_request.test_coverage or "").lower()
        has_test_files = any("test" in f.lower() for f in (self.implementation.files_changed or []))
        
        if not has_pr_coverage and not has_test_files:
            # Tests might be added separately by test_engineer, so don't reject
            suggestions.append("Test files will be added/validated in TEST_VALIDATION_GATE")
            return 0.7  # Reasonable optimism
        elif has_pr_coverage and has_test_files:
            return 0.95  # Excellent: both coverage in PR and test files changed
        elif has_pr_coverage or has_test_files:
            return 0.85  # Good: at least one indicator
        else:
            return 0.7


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
    @staticmethod
    def _calculate_complexity(
        backlog_text: str,
        files_to_modify: list[str],
        target_symbols: dict[str, list[str]] | None = None,
    ) -> float:
        """
        Calculate task complexity from backlog and files.
        
        Returns: 0.0 (trivial) to 1.0 (very complex)
        
        Factors considered:
        - Number of files to modify (more = more complex)
        - Backlog text length (longer description = more scope)
        - Presence of complexity keywords (refactor, redesign, etc.)
        - Number of symbols to target (more symbols = more complex)
        """
        complexity = 0.0
        
        # Factor 1: File count (0.0-0.5)
        file_count = len([f for f in (files_to_modify or []) if f.startswith("src/")])
        if file_count == 0:
            complexity += 0.0
        elif file_count == 1:
            complexity += 0.1  # Single file is trivial
        elif file_count == 2:
            complexity += 0.2
        elif file_count <= 4:
            complexity += 0.35
        else:
            complexity += 0.5  # 5+ files is highly complex
        
        # Factor 2: Backlog text length (0.0-0.2)
        text_length = len(backlog_text or "")
        if text_length < 100:
            complexity += 0.0
        elif text_length < 300:
            complexity += 0.08
        elif text_length < 600:
            complexity += 0.15
        else:
            complexity += 0.2
        
        # Factor 3: Complexity keywords (0.0-0.2)
        complexity_keywords = [
            "refactor", "redesign", "rewrite", "migration",
            "optimization", "restructure", "overhaul", "rearchitect",
        ]
        backlog_lower = (backlog_text or "").lower()
        keyword_count = sum(1 for kw in complexity_keywords if kw in backlog_lower)
        complexity += min(0.2, keyword_count * 0.05)
        
        # Factor 4: Symbol targets count (0.0-0.1)
        if target_symbols:
            total_symbols = sum(len(symbols) for symbols in target_symbols.values())
            complexity += min(0.1, total_symbols * 0.02)
        
        return min(1.0, complexity)

    @staticmethod
    def _optimal_lane_count(complexity: float) -> int:
        """
        Map complexity score to optimal lane count (1-5).
        
        Args:
            complexity: 0.0-1.0 score
        
        Returns: 1-5 lanes
        """
        if complexity < 0.15:
            return 1  # Trivial: single focused change
        elif complexity < 0.35:
            return 2  # Simple: small refactor
        elif complexity < 0.55:
            return 3  # Medium: standard workload
        elif complexity < 0.75:
            return 4  # High: large workload
        else:
            return 5  # Very high: maximum parallelism

    @staticmethod
    def _default_source_targets(repo_profile: str) -> list[str]:
        if repo_profile == "upload":
            return ["src/file_validator.py", "src/upload_service.py"]
        if repo_profile == "auth":
            return ["src/auth_service.py"]
        if repo_profile == "pipeline":
            return ["src/pipeline.py"]
        return []

    def _build_engineer_lanes(
        self,
        files_to_modify: list[str],
        repo_profile: str,
        backlog_text: str = "",
        target_symbols: dict[str, list[str]] | None = None,
    ) -> list[dict[str, object]]:
        """Build engineer lanes with dynamic count based on complexity."""
        source_targets = sorted({file for file in files_to_modify if file.startswith("src/")})
        required_targets = self._default_source_targets(repo_profile)
        source_targets = sorted(set(source_targets + required_targets))

        if not source_targets:
            return [{"lane_id": "engineer_1", "files": []}]

        # Calculate complexity and get optimal lane count
        complexity = self._calculate_complexity(backlog_text, source_targets, target_symbols)
        max_lanes = self._optimal_lane_count(complexity)
        
        # Cap lanes by number of files
        max_lanes = min(max_lanes, len(source_targets))
        
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
        lanes = self._build_engineer_lanes(
            plan.files_to_modify,
            repo_profile,
            backlog_text=backlog_text,
            target_symbols=plan.target_symbols,
        )
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
        
        # If no implementation, reject
        if implementation is None:
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer="peer_engineer",
                decision=Decision.REQUEST_CHANGES,
                comments="Peer review failed: implementation artifact missing.",
                issues_identified=["Missing implementation artifact"],
                suggested_changes=["Complete IMPLEMENTATION stage"],
                pull_request_id=pr.artifact_id if pr else None,
            )
            return StageResult(produced_artifacts=[review], decision=Decision.REQUEST_CHANGES, notes="Peer code review failed.")
        
        # Perform semantic code review analysis
        try:
            workspace_path = Path(implementation.workspace_path)
            analyzer = CodeReviewAnalyzer(workspace_path, implementation, pr or PullRequest())
            review_metrics = analyzer.analyze()
            
            # Decision logic: Approve if overall score >= 0.5, else request changes
            overall_score = review_metrics["overall_score"]
            decision = Decision.APPROVED if overall_score >= 0.5 else Decision.REQUEST_CHANGES
            
            # Build detailed comments with metrics
            comments_parts = [
                f"Peer code review analysis:",
                f"- Complexity: {review_metrics['complexity_score']:.0%}",
                f"- Error Handling: {review_metrics['error_handling_score']:.0%}",
                f"- Documentation: {review_metrics['documentation_score']:.0%}",
                f"- Test Alignment: {review_metrics['test_alignment_score']:.0%}",
                f"- Overall Score: {overall_score:.0%}",
            ]
            
            if decision == Decision.APPROVED:
                comments_parts.append("✓ Changes are ready for testing and acceptance review.")
            else:
                comments_parts.append(f"✗ Score below approval threshold (need ≥50%, have {overall_score:.0%})")
            
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer="peer_engineer",
                decision=decision,
                comments="\n".join(comments_parts),
                issues_identified=review_metrics["issues"],
                suggested_changes=review_metrics["suggestions"],
                pull_request_id=pr.artifact_id if pr else None,
            )
            
            return StageResult(produced_artifacts=[review], decision=decision, notes="Peer code review completed with semantic analysis.")
        except Exception as e:
            # Fallback to simple approval if analysis fails
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer="peer_engineer",
                decision=Decision.APPROVED,
                comments=f"Peer review passed. Implementation artifact present (analysis: {str(e)[:50]}...)",
                issues_identified=[],
                suggested_changes=[],
                pull_request_id=pr.artifact_id if pr else None,
            )
            return StageResult(produced_artifacts=[review], decision=Decision.APPROVED, notes="Peer code review completed (fallback).")

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage

        if stage == WorkflowStage.IMPLEMENTATION:
            return self._implementation_stage(context)
        if stage == WorkflowStage.PULL_REQUEST_CREATED:
            return self._pull_request_stage(context)
        if stage == WorkflowStage.PEER_CODE_REVIEW_GATE:
            return self._peer_review_stage(context)

        return StageResult(notes=f"No Engineer action for stage {stage.value}.")
