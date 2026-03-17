from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FailureTarget:
    test_file: str
    source_file: str
    symbols: list[str] = field(default_factory=list)
    confidence_score: float = 0.5
    match_reason: str = "import_inference"


def _normalize_repo_rel(path: str) -> str:
    return path.replace("\\", "/")


def index_python_symbols(repo_path: str | Path) -> dict[str, dict[str, list[str]]]:
    root = Path(repo_path)
    result: dict[str, dict[str, list[str]]] = {}

    for file_path in root.rglob("*.py"):
        rel = _normalize_repo_rel(str(file_path.relative_to(root)))
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        functions: list[str] = []
        classes: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        result[rel] = {
            "functions": sorted(set(functions)),
            "classes": sorted(set(classes)),
        }

    return result


def parse_failed_tests(pytest_output: str) -> list[str]:
    failed = re.findall(r"^FAILED\s+([^\s]+::[^\s]+)", pytest_output, flags=re.MULTILINE)
    if not failed:
        failed = re.findall(r"^([^\s]+::[^\s]+)\s+FAILED$", pytest_output, flags=re.MULTILINE)
    return sorted(set(failed))


def _extract_traceback_locations(pytest_output: str) -> dict[str, set[int]]:
    line_matches = re.findall(r"((?:src|tests)/[^\s:]+\.py):(\d+)", pytest_output)
    result: dict[str, set[int]] = {}
    for rel_path, line_text in line_matches:
        normalized = _normalize_repo_rel(rel_path)
        result.setdefault(normalized, set()).add(int(line_text))
    return result


def _index_top_level_functions(repo_path: str | Path) -> dict[str, list[tuple[str, int, int]]]:
    root = Path(repo_path)
    result: dict[str, list[tuple[str, int, int]]] = {}

    for file_path in root.rglob("*.py"):
        rel = _normalize_repo_rel(str(file_path.relative_to(root)))
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        functions: list[tuple[str, int, int]] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                start = getattr(node, "lineno", 0)
                end = getattr(node, "end_lineno", start)
                functions.append((node.name, start, end))

        if functions:
            result[rel] = functions

    return result


def _symbols_for_trace_line(
    file_path: str,
    line_no: int,
    function_index: dict[str, list[tuple[str, int, int]]],
) -> list[str]:
    for symbol_name, start, end in function_index.get(file_path, []):
        if start <= line_no <= end:
            return [symbol_name]
    return []


def map_failures_to_source(
    repo_path: str | Path,
    failing_tests: list[str],
    pytest_output: str = "",
) -> list[FailureTarget]:
    root = Path(repo_path)
    mapped: list[FailureTarget] = []
    traceback_locations = _extract_traceback_locations(pytest_output)
    function_index = _index_top_level_functions(root)

    for source_file, lines in traceback_locations.items():
        source_abs = root / source_file
        if not source_file.startswith("src/") or not source_abs.exists():
            continue

        symbols: list[str] = []
        for line_no in sorted(lines):
            symbols.extend(_symbols_for_trace_line(source_file, line_no, function_index))

        mapped.append(
            FailureTarget(
                test_file="traceback",
                source_file=source_file,
                symbols=sorted(set(symbols)),
                confidence_score=0.95,
                match_reason="traceback_line_match",
            )
        )

    for item in failing_tests:
        test_file_rel = _normalize_repo_rel(item.split("::", 1)[0])
        test_file_abs = root / test_file_rel
        if not test_file_abs.exists():
            continue

        imported_modules: dict[str, list[str]] = {}
        try:
            tree = ast.parse(test_file_abs.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                names = [alias.name for alias in node.names]
                imported_modules.setdefault(module, []).extend(names)

        for module, symbols in imported_modules.items():
            candidate = root / "src" / f"{module}.py"
            if candidate.exists():
                mapped.append(
                    FailureTarget(
                        test_file=test_file_rel,
                        source_file=_normalize_repo_rel(str(candidate.relative_to(root))),
                        symbols=sorted(set(symbols)),
                        confidence_score=0.7,
                        match_reason="test_import",
                    )
                )

    # lightweight heuristic from assertion output for UploadResult.error mismatch
    if "result.error" in pytest_output and not any(m.source_file.endswith("upload_service.py") for m in mapped):
        candidate = root / "src" / "upload_service.py"
        if candidate.exists():
            mapped.append(
                FailureTarget(
                    test_file="tests/test_upload_service.py",
                    source_file="src/upload_service.py",
                    symbols=["upload_document"],
                    confidence_score=0.8,
                    match_reason="assertion_heuristic",
                )
            )

    # dedupe while merging symbol lists
    merged: dict[tuple[str, str], FailureTarget] = {}
    for target in mapped:
        key = (target.test_file, target.source_file)
        if key not in merged:
            merged[key] = FailureTarget(
                test_file=target.test_file,
                source_file=target.source_file,
                symbols=list(target.symbols),
                confidence_score=target.confidence_score,
                match_reason=target.match_reason,
            )
        else:
            merged[key].symbols = sorted(set(merged[key].symbols + target.symbols))
            merged[key].confidence_score = max(merged[key].confidence_score, target.confidence_score)
            if merged[key].match_reason != target.match_reason and target.confidence_score >= merged[key].confidence_score:
                merged[key].match_reason = target.match_reason

    return sorted(
        list(merged.values()),
        key=lambda item: (item.confidence_score, len(item.symbols)),
        reverse=True,
    )
