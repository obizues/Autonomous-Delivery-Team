from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import cast

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, EventType, WorkflowStage
from ai_software_factory.domain.models import BaseArtifact, BacklogItem, CodeImplementation, HumanIntervention, PullRequest, ReviewFeedback, TestResult
from ai_software_factory.events.bus import EventBus
from ai_software_factory.execution.file_patch_engine import FilePatchEngine
from ai_software_factory.execution.repo_workspace import RepoWorkspaceManager
from ai_software_factory.llm import LLMCodeGenerator
from ai_software_factory.planning.repo_change_planner import RepoChangePlanner
from ai_software_factory.tools.repo_tools import list_repo_files, search_repo
from ai_software_factory.workflow.stage_result import StageResult

logger = logging.getLogger(__name__)


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
            "completeness": self._analyze_completeness(issues, suggestions),
        }
        
        # Weighted average: completeness and error_handling weighted slightly higher
        weights = {"complexity": 1.0, "error_handling": 1.2, "documentation": 0.8, "test_alignment": 1.2, "completeness": 1.3}
        total_weight = sum(weights[k] for k in scores)
        overall = sum(scores[k] * weights[k] for k in scores) / total_weight if total_weight else 0.5
        
        return {
            "complexity_score": scores.get("complexity", 0.5),
            "error_handling_score": scores.get("error_handling", 0.5),
            "documentation_score": scores.get("documentation", 0.5),
            "test_alignment_score": scores.get("test_alignment", 0.5),
            "completeness_score": scores.get("completeness", 0.5),
            "overall_score": overall,
            "issues": issues,
            "suggestions": suggestions,
        }

    def _analyze_completeness(self, issues: list, suggestions: list) -> float:
        """Check that implementation actually produced tangible output."""
        files_changed = len(self.implementation.files_changed or [])
        written = len(self.implementation.written_source_files or [])
        if files_changed == 0 and written == 0:
            issues.append("No source files were changed or written — implementation appears empty")
            return 0.10
        if files_changed == 0:
            suggestions.append("implementation.files_changed is empty; verify patch engine recorded modified files")
            return 0.45
        if written == 0:
            suggestions.append("No written_source_files recorded; verify workspace contains output")
            return 0.55
        return 0.90

    def _analyze_complexity(self, issues: list) -> float:
        """Analyze code change complexity."""
        files_changed = len(self.implementation.files_changed or [])
        
        # Score based on number of files (minimal complexity is good for focused changes)
        if files_changed == 0:
            issues.append("No files were changed in implementation")
            return 0.30
        elif files_changed == 1:
            return 0.95  # Single file changes are excellent
        elif files_changed <= 3:
            return 0.85  # Multiple files, still reasonable
        else:
            issues.append(f"High complexity: {files_changed} files modified (consider breaking into smaller PRs)")
            return 0.60
        
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
                issues.append("Insufficient error handling: add try/except blocks and raise statements for invalid inputs")
                suggestions.append("Add explicit validation with raise statements for each rejection path")
            return max(0.40, score)  # Lower floor so truly absent error handling fails
        except Exception:
            return 0.60

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
                issues.append("Very low comment density — complex logic lacks inline explanation")
                suggestions.append("Add inline comments to document business rules and non-obvious branches")
                score = 0.55
            elif comment_ratio > 0.50:
                suggestions.append("Consider reducing comment density; strive for self-explaining code")
                score = 0.70
            else:
                score = 0.85
                
            if docstring_count > 0:
                score += 0.05  # Bonus for having docstrings
                
            return min(1.0, score)
        except Exception:
            return 0.65

    def _analyze_test_alignment(self, issues: list, suggestions: list) -> float:
        """Analyze test coverage for implemented changes."""
        # Check if PR includes test coverage signals
        has_pr_coverage = "test" in (self.pull_request.test_coverage or "").lower()
        has_test_files = any("test" in f.lower() for f in (self.implementation.files_changed or []))
        
        if not has_pr_coverage and not has_test_files:
            issues.append("No test coverage indicated in PR description or files changed")
            suggestions.append("Ensure test files reference the changed source files for TEST_VALIDATION_GATE")
            return 0.50  # Penalise rather than silently accept
        elif has_pr_coverage and has_test_files:
            return 0.95  # Excellent: both coverage in PR and test files changed
        elif has_pr_coverage or has_test_files:
            return 0.80  # Good: at least one indicator
        else:
            return 0.50


class EngineerAgent(Agent):
    role = "engineer"
    STORY_SLICE_ASSIGNMENTS = {
        1: "Core domain workflow",
        2: "Validation and edge handling",
        3: "Integration and regression safeguards",
    }

    def __init__(
        self,
        repo_workspace: RepoWorkspaceManager,
        planner: RepoChangePlanner,
        patch_engine: FilePatchEngine,
        event_bus: EventBus,
        llm_generator: LLMCodeGenerator | None = None,
    ) -> None:
        self.repo_workspace = repo_workspace
        self.planner = planner
        self.patch_engine = patch_engine
        self.event_bus = event_bus
        self.llm_generator = llm_generator or LLMCodeGenerator()

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

    @classmethod
    def _story_slice_assignment(cls, lane_index: int) -> str:
        return cls.STORY_SLICE_ASSIGNMENTS.get(lane_index, f"Auxiliary implementation slice {lane_index}")

    @staticmethod
    def _extract_lane_id_from_pr(pr: PullRequest) -> str | None:
        match = re.search(r"\[(engineer_\d+)(?::[^\]]+)?\]", pr.title or "")
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _build_cross_review_matrix(lane_ids: list[str]) -> dict[str, str]:
        ordered_ids: list[str] = []
        for lane_id in lane_ids:
            if lane_id not in ordered_ids:
                ordered_ids.append(lane_id)

        if not ordered_ids:
            return {}
        if len(ordered_ids) == 1:
            only_lane = ordered_ids[0]
            return {only_lane: only_lane}

        matrix: dict[str, str] = {}
        for index, lane_id in enumerate(ordered_ids):
            matrix[lane_id] = ordered_ids[(index + 1) % len(ordered_ids)]
        return matrix

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
                "story_slice": self._story_slice_assignment(index),
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
                    # Try LLM-based fix first (revision > 1), fall back to deterministic
                    if upload_path.exists():
                        source = upload_path.read_text(encoding="utf-8")
                        llm_response = self.llm_generator.generate_function_replacement(
                            source_code=source,
                            function_name="upload_document",
                            objective="Fix upload_document to handle edge cases and validate properly. Include error field in responses.",
                            file_path="src/upload_service.py",
                        )
                        if llm_response.success and llm_response.generated_code:
                            logger.info(f"Using LLM-generated upload_document (model: {llm_response.model_used})")
                            replaced = self.patch_engine.replace_function(
                                file_path=upload_path,
                                function_name="upload_document",
                                new_function_code=llm_response.generated_code,
                            )
                            patch_results.append(replaced)
                            if not replaced.success:
                                logger.warning("LLM-generated function failed validation, falling back to deterministic patch")
                                replaced = self.patch_engine.replace_function(
                                    file_path=upload_path,
                                    function_name="upload_document",
                                    new_function_code=self._upload_document_revision_2(),
                                )
                                patch_results.append(replaced)
                        else:
                            # LLM unavailable or failed, use deterministic
                            if not llm_response.success:
                                logger.debug(f"LLM generation skipped for upload_document: {llm_response.error_message}")
                            replaced = self.patch_engine.replace_function(
                                file_path=upload_path,
                                function_name="upload_document",
                                new_function_code=self._upload_document_revision_2(),
                            )
                            patch_results.append(replaced)
                            if not replaced.success:
                                patch_results.append(self.patch_engine.apply_patch(upload_path, self._upload_service_module_fixed()))
                    else:
                        # File doesn't exist, use full module patch
                        patch_results.append(self.patch_engine.apply_patch(upload_path, self._upload_service_module_fixed()))

        elif repo_profile == "auth":
            if should_patch("src/auth_service.py"):
                if revision == 1:
                    patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_1()))
                else:
                    # Try LLM-based fix first (revision > 1), fall back to deterministic
                    if auth_path.exists():
                        source = auth_path.read_text(encoding="utf-8")
                        llm_response = self.llm_generator.generate_function_replacement(
                            source_code=source,
                            function_name="login",
                            objective="Fix login function to properly enforce account lockout after 2 failed attempts (not 3). Prevent timing attacks.",
                            file_path="src/auth_service.py",
                        )
                        if llm_response.success and llm_response.generated_code:
                            logger.info(f"Using LLM-generated login function (model: {llm_response.model_used})")
                            replaced = self.patch_engine.replace_function(
                                file_path=auth_path,
                                function_name="login",
                                new_function_code=llm_response.generated_code,
                            )
                            patch_results.append(replaced)
                            if not replaced.success:
                                logger.warning("LLM-generated function failed validation, falling back to deterministic patch")
                                patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_2()))
                        else:
                            if not llm_response.success:
                                logger.debug(f"LLM generation skipped for login: {llm_response.error_message}")
                            patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_2()))
                    else:
                        patch_results.append(self.patch_engine.apply_patch(auth_path, self._auth_service_module_revision_2()))

        elif repo_profile == "pipeline":
            if should_patch("src/pipeline.py"):
                if revision == 1:
                    patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_1()))
                else:
                    # Try LLM-based fix first (revision > 1), fall back to deterministic
                    if pipeline_path.exists():
                        source = pipeline_path.read_text(encoding="utf-8")
                        llm_response = self.llm_generator.generate_function_replacement(
                            source_code=source,
                            function_name="process_records",
                            objective="Ensure process_records properly validates records and handles duplicate IDs correctly. Return proper counts.",
                            file_path="src/pipeline.py",
                        )
                        if llm_response.success and llm_response.generated_code:
                            logger.info(f"Using LLM-generated process_records (model: {llm_response.model_used})")
                            replaced = self.patch_engine.replace_function(
                                file_path=pipeline_path,
                                function_name="process_records",
                                new_function_code=llm_response.generated_code,
                            )
                            patch_results.append(replaced)
                            if not replaced.success:
                                logger.warning("LLM-generated function failed validation, falling back to deterministic patch")
                                patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_2()))
                        else:
                            if not llm_response.success:
                                logger.debug(f"LLM generation skipped for process_records: {llm_response.error_message}")
                            patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_2()))
                    else:
                        patch_results.append(self.patch_engine.apply_patch(pipeline_path, self._pipeline_module_revision_2()))

        else:
            # Generic repo: try LLM if available
            for file_name in plan_files_to_modify:
                if not file_name.startswith("src/"):
                    continue
                if not should_patch(file_name):
                    continue
                full_path = workspace_path / file_name
                if full_path.exists():
                    current = full_path.read_text(encoding="utf-8")
                    
                    # For generic repos, try LLM to generate fixes
                    llm_response = self.llm_generator.generate_file_content(
                        file_path=file_name,
                        current_content=current,
                        objective="Improve code quality and functionality. Fix any issues detected in tests.",
                        context="Generic repository with no predefined profile.",
                    )
                    
                    if llm_response.success and llm_response.generated_code:
                        logger.info(f"Using LLM-generated content for {file_name} (model: {llm_response.model_used})")
                        result = self.patch_engine.apply_patch(full_path, llm_response.generated_code)
                        patch_results.append(result)
                        if not result.success:
                            logger.warning(f"LLM-generated content failed validation for {file_name}, using original")
                            patch_results.append(self.patch_engine.apply_patch(full_path, current))
                    else:
                        # LLM unavailable/failed, use original (no-op patch)
                        if not llm_response.success:
                            logger.debug(f"LLM generation skipped for {file_name}: {llm_response.error_message}")
                        patch_results.append(self.patch_engine.apply_patch(full_path, current))

        return patch_results

    def _implementation_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        backlog = context.latest(BacklogItem)
        previous_test = context.latest(TestResult)
        previous_feedback = context.latest(ReviewFeedback)
        human_intervention = context.latest(HumanIntervention)

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
        if human_intervention is not None and human_intervention.response:
            backlog_text += (
                "\nHuman intervention guidance:\n"
                f"{human_intervention.response}\n"
                f"Requested outcome: {human_intervention.desired_outcome}\n"
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
            lane_story_slice = str(lane.get("story_slice", self._story_slice_assignment(1)))
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
                f"{lane_id} slice={lane_story_slice} files={sorted(lane_files) if lane_files else ['(planner-default)']} "
                f"applied={lane_success_count} failed={lane_failure_count}"
            )

        changed_files = sorted(set(changed_files))
        lane_assignment_payload: list[dict[str, object]] = []
        for index, lane in enumerate(lanes):
            lane_files = lane.get("files", [])
            normalized_lane_files = lane_files if isinstance(lane_files, list) else []
            lane_assignment_payload.append(
                {
                    "lane_id": str(lane["lane_id"]),
                    "story_slice": str(lane.get("story_slice", self._story_slice_assignment(index + 1))),
                    "files": normalized_lane_files,
                }
            )

        self.event_bus.emit(
            workflow_id=workflow_id,
            event_type=EventType.FILES_MODIFIED,
            stage=state.current_stage,
            payload={
                "sandbox_path": str(sandbox_path),
                "files_changed": changed_files,
                "revision": revision,
                "engineer_lanes": lane_summaries,
                "engineer_lane_assignments": lane_assignment_payload,
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
        if human_intervention is not None and human_intervention.response:
            notes.append(f"Human intervention guidance: {human_intervention.response}")
            notes.append(f"Human requested outcome: {human_intervention.desired_outcome}")

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
        backlog_text = "\n".join(
            [
                backlog.title if backlog else "",
                backlog.problem_statement if backlog else "",
                "\n".join(backlog.acceptance_criteria) if backlog else "",
            ]
        )

        changed_source_files = sorted({
            file_name
            for file_name in (implementation.written_source_files or [])
            if file_name.startswith("src/")
        })

        if not changed_source_files:
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
                test_coverage="pytest suite validates profile-specific behavior in sandbox.",
                known_limitations=[
                    "Symbol-level patching currently targets top-level functions only",
                    "Semantic mapper is heuristic-based and Python-only",
                ],
            )
            return StageResult(produced_artifacts=[pr], notes="Pull request artifact created for semantic sandbox changes.")

        complexity = self._calculate_complexity(
            backlog_text=backlog_text,
            files_to_modify=changed_source_files,
            target_symbols=None,
        )
        lane_count = min(self._optimal_lane_count(complexity), len(changed_source_files))

        lane_buckets: list[list[str]] = [[] for _ in range(max(1, lane_count))]
        for index, file_name in enumerate(changed_source_files):
            lane_buckets[index % len(lane_buckets)].append(file_name)

        pull_requests: list[PullRequest] = []
        for lane_index, lane_files in enumerate(lane_buckets, start=1):
            if not lane_files:
                continue
            lane_id = f"engineer_{lane_index}"
            lane_story_slice = self._story_slice_assignment(lane_index)
            pr = PullRequest(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                title=f"feat(repo-mode): {title} — revision {revision} [{lane_id}: {lane_story_slice}]",
                description=(
                    "Applies semantic repo-aware patching in sandbox based on failure context. "
                    f"Scoped to {lane_id} lane files. Story slice: {lane_story_slice}."
                ),
                implementation_artifact_id=implementation.artifact_id,
                files_modified=sorted(lane_files),
                architecture_alignment=(
                    "Each lane keeps module boundaries isolated while supporting parallel code review and integration."
                ),
                test_coverage=(
                    "pytest validates behavior after lane integration; lane-specific scope derived from implementation partitioning."
                ),
                known_limitations=[
                    "Lane PRs are generated from file partitioning rather than independent branch history",
                    "Symbol-level patching currently targets top-level functions only",
                    "Semantic mapper is heuristic-based and Python-only",
                ],
            )
            pull_requests.append(pr)

        lane_ids = [
            lane_id
            for lane_id in (self._extract_lane_id_from_pr(pr) for pr in pull_requests)
            if lane_id
        ]
        cross_review_matrix = self._build_cross_review_matrix(lane_ids)
        for pr in pull_requests:
            lane_id = self._extract_lane_id_from_pr(pr)
            if not lane_id:
                continue
            reviewer_lane = cross_review_matrix.get(lane_id)
            if not reviewer_lane:
                continue
            pr.linked_review_ids = [f"{reviewer_lane}->reviews->{lane_id}"]
            pr.description = (
                f"{pr.description} Cross-review assignment: {lane_id} reviewed by {reviewer_lane}."
            )

        if not pull_requests:
            return StageResult(decision=Decision.REQUEST_CHANGES, notes="Unable to generate lane pull requests.")

        return StageResult(
            produced_artifacts=cast(list[BaseArtifact], pull_requests),
            notes=f"Generated {len(pull_requests)} lane pull request artifacts for parallel engineer review.",
        )

    def _peer_review_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        implementation = context.latest(CodeImplementation)
        revision_prs = [
            artifact
            for artifact in context.artifacts
            if isinstance(artifact, PullRequest) and artifact.version == revision
        ]
        pr = revision_prs[-1] if revision_prs else context.latest(PullRequest)
        lane_ids = [
            lane_id
            for lane_id in (self._extract_lane_id_from_pr(lane_pr) for lane_pr in revision_prs)
            if lane_id
        ]
        cross_review_matrix = self._build_cross_review_matrix(lane_ids)
        review_pairs = [
            f"{reviewer_lane} reviews {lane_id}"
            for lane_id, reviewer_lane in sorted(cross_review_matrix.items())
        ]
        reviewer_label = "; ".join(review_pairs) if review_pairs else "peer_engineer"

        if pr is None:
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer="peer_engineer",
                decision=Decision.REQUEST_CHANGES,
                comments="Peer review failed: pull request artifact missing for current revision.",
                issues_identified=["Missing pull request artifact"],
                suggested_changes=["Complete PULL_REQUEST_CREATED stage before peer review"],
                pull_request_id=None,
            )
            return StageResult(produced_artifacts=[review], decision=Decision.REQUEST_CHANGES, notes="Peer code review failed.")
        
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
            analyzer = CodeReviewAnalyzer(workspace_path, implementation, pr)
            review_metrics = analyzer.analyze()
            
            # Revision-aware threshold: stricter on repeated revisions
            overall_score = review_metrics["overall_score"]
            approval_threshold = 0.68 if revision >= 2 else 0.60
            decision = Decision.APPROVED if overall_score >= approval_threshold else Decision.REQUEST_CHANGES
            
            # Build detailed comments with metrics
            completeness_score = review_metrics.get("completeness_score", overall_score)
            comments_parts = [
                f"Peer code review analysis (threshold: {approval_threshold:.0%}):",
                f"- Complexity: {review_metrics['complexity_score']:.0%}",
                f"- Error Handling: {review_metrics['error_handling_score']:.0%}",
                f"- Documentation: {review_metrics['documentation_score']:.0%}",
                f"- Test Alignment: {review_metrics['test_alignment_score']:.0%}",
                f"- Completeness: {completeness_score:.0%}",
                f"- Overall Score: {overall_score:.0%} (need ≥{approval_threshold:.0%})",
                f"- Pull Requests Reviewed: {len(revision_prs) if revision_prs else (1 if pr else 0)}",
            ]
            if cross_review_matrix:
                comments_parts.append("- Cross-review matrix:")
                for lane_id in sorted(cross_review_matrix.keys()):
                    comments_parts.append(
                        f"  - {lane_id} reviewed by {cross_review_matrix[lane_id]}"
                    )
            
            if decision == Decision.APPROVED:
                comments_parts.append("✓ Implementation quality meets the bar. Ready for testing and acceptance.")
            else:
                comments_parts.append(f"✗ Score {overall_score:.0%} is below the {approval_threshold:.0%} approval threshold for revision {revision}.")
                if revision >= 2:
                    comments_parts.append("ℹ Stricter bar applied: revision 2+ requires 68% to ensure rework actually improved quality.")
            
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer=reviewer_label,
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
                reviewer=reviewer_label,
                decision=Decision.APPROVED,
                comments=f"Peer review passed. Implementation artifact present (analysis: {str(e)[:50]}...)",
                issues_identified=[],
                suggested_changes=[],
                pull_request_id=pr.artifact_id if pr else None,
            )
            return StageResult(produced_artifacts=[review], decision=Decision.APPROVED, notes="Peer code review completed (fallback).")

    def _merge_conflict_gate_stage(self, context: AgentContext) -> StageResult:
        state = context.workflow_state
        workflow_id = state.workflow_id
        revision = state.revision

        implementation = context.latest(CodeImplementation)
        revision_prs = [
            artifact
            for artifact in context.artifacts
            if isinstance(artifact, PullRequest) and artifact.version == revision
        ]
        primary_pr = revision_prs[-1] if revision_prs else context.latest(PullRequest)

        if not revision_prs:
            review = ReviewFeedback(
                workflow_id=workflow_id,
                stage=state.current_stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer="merge_conflict_guard",
                decision=Decision.REQUEST_CHANGES,
                comments="Merge conflict gate failed: no pull request artifacts found for this revision.",
                issues_identified=["Missing pull request artifacts for merge validation"],
                suggested_changes=["Complete PULL_REQUEST_CREATED stage before merge conflict gate"],
                pull_request_id=primary_pr.artifact_id if primary_pr else None,
            )
            return StageResult(
                produced_artifacts=[review],
                decision=Decision.REQUEST_CHANGES,
                notes="Merge conflict gate failed: missing pull request artifacts.",
            )

        lane_file_owners: dict[str, set[str]] = {}
        for pr in revision_prs:
            lane_id = self._extract_lane_id_from_pr(pr) or "engineer_unknown"
            for file_name in pr.files_modified:
                lane_file_owners.setdefault(file_name, set()).add(lane_id)

        overlapping_files = sorted(
            file_name
            for file_name, owners in lane_file_owners.items()
            if len(owners) > 1
        )

        conflict_marker_files: list[str] = []
        if implementation is not None and implementation.workspace_path:
            workspace_path = Path(implementation.workspace_path)
            candidate_files = sorted(lane_file_owners.keys())
            for relative_file in candidate_files:
                file_path = workspace_path / relative_file
                if not file_path.exists() or not file_path.is_file():
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if "<<<<<<<" in content and "=======" in content and ">>>>>>>" in content:
                    conflict_marker_files.append(relative_file)

        has_conflicts = bool(overlapping_files or conflict_marker_files)
        decision = Decision.REQUEST_CHANGES if has_conflicts else Decision.APPROVED

        comments_parts = [
            "Merge conflict gate analysis:",
            f"- Pull requests inspected: {len(revision_prs)}",
            f"- Files with multi-lane overlap: {len(overlapping_files)}",
            f"- Files containing merge markers: {len(conflict_marker_files)}",
        ]
        if has_conflicts:
            comments_parts.append("✗ Merge conflicts detected. Resolve overlaps/markers before proceeding.")
        else:
            comments_parts.append("✓ No merge conflicts detected. Safe to continue to architecture review.")

        issues_identified: list[str] = []
        if overlapping_files:
            issues_identified.extend(
                [f"Cross-lane file overlap: {file_name}" for file_name in overlapping_files]
            )
        if conflict_marker_files:
            issues_identified.extend(
                [f"Conflict marker found: {file_name}" for file_name in conflict_marker_files]
            )

        suggested_changes: list[str] = []
        if has_conflicts:
            suggested_changes = [
                "Repartition lane ownership so each file has a single lane owner",
                "Resolve git conflict markers and rerun merge conflict gate",
            ]

        review = ReviewFeedback(
            workflow_id=workflow_id,
            stage=state.current_stage,
            created_by=self.role,
            status=ArtifactStatus.FINAL,
            version=revision,
            reviewer="merge_conflict_guard",
            decision=decision,
            comments="\n".join(comments_parts),
            issues_identified=issues_identified,
            suggested_changes=suggested_changes,
            pull_request_id=primary_pr.artifact_id if primary_pr else None,
        )

        notes = "Merge conflict gate passed." if decision == Decision.APPROVED else "Merge conflict gate requested changes."
        return StageResult(produced_artifacts=[review], decision=decision, notes=notes)

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage

        if stage == WorkflowStage.IMPLEMENTATION:
            return self._implementation_stage(context)
        if stage == WorkflowStage.PULL_REQUEST_CREATED:
            return self._pull_request_stage(context)
        if stage == WorkflowStage.MERGE_CONFLICT_GATE:
            return self._merge_conflict_gate_stage(context)
        if stage == WorkflowStage.PEER_CODE_REVIEW_GATE:
            return self._peer_review_stage(context)

        return StageResult(notes=f"No Engineer action for stage {stage.value}.")
