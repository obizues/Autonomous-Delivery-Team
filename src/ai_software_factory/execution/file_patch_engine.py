from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatchResult:
    file_path: str
    operation: str
    success: bool
    rolled_back: bool
    message: str
    symbols: list[str] = field(default_factory=list)


from typing import Optional

class FilePatchEngine:
    @staticmethod
    def _should_validate_python(target: Path) -> bool:
        return target.suffix == ".py"

    @staticmethod
    def _validate_python(content: str) -> tuple[bool, str]:
        try:
            ast.parse(content)
            return True, ""
        except SyntaxError as exc:
            return False, f"SyntaxError: {exc.msg} at line {exc.lineno}"

    def _write_with_validation(self, target: Path, content: str, operation: str, symbols: list[str] | None = None) -> PatchResult:
        target.parent.mkdir(parents=True, exist_ok=True)

        had_original = target.exists()
        original_content = target.read_text(encoding="utf-8") if had_original else ""
        normalized = content.rstrip() + "\n"

        target.write_text(normalized, encoding="utf-8")

        if self._should_validate_python(target):
            ok, reason = self._validate_python(normalized)
            if not ok:
                if had_original:
                    target.write_text(original_content, encoding="utf-8")
                else:
                    target.unlink(missing_ok=True)
                return PatchResult(
                    file_path=str(target),
                    operation=operation,
                    success=False,
                    rolled_back=True,
                    message=f"Patch rolled back due to invalid Python syntax. {reason}",
                    symbols=symbols or [],
                )

        return PatchResult(
            file_path=str(target),
            operation=operation,
            success=True,
            rolled_back=False,
            message="Patch applied successfully.",
            symbols=symbols or [],
        )

    def apply_patch(self, file_path: str | Path, new_content: str) -> PatchResult:
        target = Path(file_path)
        return self._write_with_validation(target, new_content, operation="apply_patch")

    def append_code(self, file_path: str | Path, code_block: str) -> PatchResult:
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        combined = existing.rstrip() + "\n\n" + code_block.rstrip() + "\n"
        return self._write_with_validation(target, combined, operation="append_code")

    def replace_function(self, file_path: str | Path, function_name: str, new_function_code: str) -> PatchResult:
        target = Path(file_path)
        if not target.exists():
            return PatchResult(
                file_path=str(target),
                operation="replace_function",
                success=False,
                rolled_back=False,
                message="Target file does not exist.",
                symbols=[function_name],
            )

        source = target.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                start = node.lineno - 1
                end = node.end_lineno
                replacement_lines = new_function_code.rstrip().splitlines()
                updated = lines[:start] + replacement_lines + lines[end:]
                return self._write_with_validation(
                    target,
                    "\n".join(updated),
                    operation="replace_function",
                    symbols=[function_name],
                )

        return PatchResult(
            file_path=str(target),
            operation="replace_function",
            success=False,
            rolled_back=False,
            message=f"Function '{function_name}' not found.",
            symbols=[function_name],
        )
