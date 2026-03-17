from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_software_factory.domain.enums import IntentCategory
from ai_software_factory.tools.repo_tools import get_test_files, list_repo_files
from ai_software_factory.tools.repo_semantic import index_python_symbols, map_failures_to_source


@dataclass
class ChangePlan:
    summary: str
    files_to_modify: list[str] = field(default_factory=list)
    files_to_create: list[str] = field(default_factory=list)
    test_changes: list[str] = field(default_factory=list)
    target_symbols: dict[str, list[str]] = field(default_factory=dict)
    target_confidence: dict[str, float] = field(default_factory=dict)
    confidence: str = "MEDIUM"
    intent_category: IntentCategory = IntentCategory.GENERAL
    risks: list[str] = field(default_factory=list)


class RepoChangePlanner:
    @staticmethod
    def classify_intent(backlog_text: str) -> IntentCategory:
        text = (backlog_text or "").lower()
        if any(token in text for token in ["validate", "validation", "reject", "constraint", "limit"]):
            return IntentCategory.VALIDATION
        if any(token in text for token in ["endpoint", "api", "contract", "payload", "response"]):
            return IntentCategory.API_CHANGE
        if any(token in text for token in ["schema", "model", "entity", "field", "dataclass"]):
            return IntentCategory.DATA_MODEL
        if any(token in text for token in ["new feature", "support", "add", "introduce", "behavior"]):
            return IntentCategory.NEW_BEHAVIOR
        if any(token in text for token in ["bug", "fix", "broken", "fails", "failure", "error"]):
            return IntentCategory.BUG_FIX
        return IntentCategory.GENERAL

    def create_plan(
        self,
        backlog_text: str,
        repo_path: str | Path,
        failing_tests: list[str] | None = None,
        failure_output: str = "",
    ) -> ChangePlan:
        intent = self.classify_intent(backlog_text)
        py_files = list_repo_files(repo_path)
        tests = get_test_files(repo_path)
        symbol_index = index_python_symbols(repo_path)

        failing_tests = failing_tests or []
        targets = map_failures_to_source(repo_path, failing_tests, failure_output) if failing_tests else []

        ranked_sources = [
            target for target in targets
            if target.source_file.startswith("src/")
        ]

        files_to_modify = [target.source_file for target in ranked_sources]

        target_symbols: dict[str, list[str]] = {}
        target_confidence: dict[str, float] = {}
        for target in ranked_sources:
            existing_symbols = target_symbols.get(target.source_file, [])
            target_symbols[target.source_file] = sorted(set(existing_symbols + target.symbols))
            target_confidence[target.source_file] = max(
                target_confidence.get(target.source_file, 0.0),
                target.confidence_score,
            )

        if not files_to_modify:
            files_to_modify = [
                "src/file_validator.py",
                "src/upload_service.py",
                "tests/test_file_validator.py",
                "tests/test_upload_service.py",
            ]
            target_symbols = {
                "src/file_validator.py": ["validate_upload"],
                "src/upload_service.py": ["upload_document"],
            }
            target_confidence = {
                "src/file_validator.py": 0.55,
                "src/upload_service.py": 0.55,
            }

        if intent == IntentCategory.DATA_MODEL:
            for rel_path, indexed in symbol_index.items():
                if rel_path.startswith("src/") and indexed.get("classes"):
                    files_to_modify.append(rel_path)
                    target_symbols.setdefault(rel_path, []).extend(indexed["classes"])
                    target_confidence[rel_path] = max(target_confidence.get(rel_path, 0.0), 0.6)

        if intent == IntentCategory.API_CHANGE:
            for rel_path, indexed in symbol_index.items():
                if rel_path.startswith("src/") and any("upload" in fn for fn in indexed.get("functions", [])):
                    files_to_modify.append(rel_path)
                    target_symbols.setdefault(rel_path, []).extend(indexed["functions"])
                    target_confidence[rel_path] = max(target_confidence.get(rel_path, 0.0), 0.65)

        target_symbols = {
            path: sorted(set(symbols))
            for path, symbols in target_symbols.items()
        }

        max_conf = max(target_confidence.values()) if target_confidence else 0.0
        confidence = "HIGH" if max_conf >= 0.85 else "MEDIUM"
        if max_conf < 0.6:
            confidence = "LOW"

        ordered_files = sorted(
            set(files_to_modify),
            key=lambda file_path: target_confidence.get(file_path, 0.0),
            reverse=True,
        )

        confidence_lines = [
            f"Target confidence {path}: {target_confidence.get(path, 0.0):.2f}"
            for path in ordered_files
        ]

        return ChangePlan(
            summary=(
                "Semantic repo plan: update upload validation and response payload behavior with "
                "targeted symbol-level changes derived from failing tests and repo index."
            ),
            files_to_modify=sorted(set(ordered_files + [
                "tests/test_file_validator.py",
                "tests/test_upload_service.py",
            ])),
            files_to_create=[],
            test_changes=[
                "Add tests for oversized file rejection",
                "Add tests asserting rejection payload includes explicit reason",
                "Keep existing accepted upload behavior tests",
                f"Repo python file count: {len(py_files)}",
                f"Indexed symbol files: {len(symbol_index)}",
            ] + confidence_lines + [f"Existing test file: {item}" for item in tests],
            target_symbols=target_symbols,
            target_confidence=target_confidence,
            confidence=confidence,
            intent_category=intent,
            risks=[
                "Overly broad validation changes could reject valid files",
                "Payload contract changes may break existing consumers",
            ],
        )
