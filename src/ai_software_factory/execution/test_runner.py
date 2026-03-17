from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TestRunResult:
    passed: bool
    failed_tests: list[str]
    new_failures: list[str]
    regression_detected: bool
    targeted_tests: list[str]
    targeted_command: str
    targeted_exit_code: int
    output: str
    exit_code: int
    stdout: str
    stderr: str
    log_path: str
    command: str


@dataclass
class TestRunOutcome:
    command: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    failing_tests: list[str]
    log_path: str


class PytestRunner:
    def run_repo_tests(
        self,
        repo_path: str | Path,
        revision: int,
        targeted_tests: list[str] | None = None,
        baseline_failures: list[str] | None = None,
    ) -> TestRunResult:
        root = Path(repo_path).resolve()
        logs_dir = root / "run_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        targeted_tests = targeted_tests or []
        baseline_failures = baseline_failures or []

        command_parts = [sys.executable, "-m", "pytest", "-q", "tests"]
        command = " ".join(command_parts)

        targeted_command_parts = [sys.executable, "-m", "pytest", "-q", *targeted_tests]
        targeted_command = " ".join(targeted_command_parts) if targeted_tests else ""

        targeted_stdout = ""
        targeted_stderr = ""
        targeted_exit_code = 0
        if targeted_tests:
            targeted_process = subprocess.run(
                targeted_command_parts,
                cwd=root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            targeted_stdout = targeted_process.stdout or ""
            targeted_stderr = targeted_process.stderr or ""
            targeted_exit_code = targeted_process.returncode

        process = subprocess.run(
            command_parts,
            cwd=root,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""
        combined_output = (stdout + "\n" + stderr).strip()
        failed_tests = self._extract_failing_tests(combined_output)
        new_failures = sorted(set(failed_tests) - set(baseline_failures))
        regression_detected = len(new_failures) > 0

        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = logs_dir / f"pytest_rev_{revision}_{stamp}.log"
        log_path.write_text(
            "\n".join(
                [
                    f"targeted_command: {targeted_command or 'N/A'}",
                    f"targeted_exit_code: {targeted_exit_code if targeted_tests else 'N/A'}",
                    "",
                    "--- targeted stdout ---",
                    targeted_stdout,
                    "",
                    "--- targeted stderr ---",
                    targeted_stderr,
                    "",
                    f"command: {command}",
                    f"exit_code: {process.returncode}",
                    f"baseline_failures: {','.join(baseline_failures) if baseline_failures else 'none'}",
                    f"new_failures: {','.join(new_failures) if new_failures else 'none'}",
                    f"regression_detected: {regression_detected}",
                    "",
                    "--- stdout ---",
                    stdout,
                    "",
                    "--- stderr ---",
                    stderr,
                ]
            ),
            encoding="utf-8",
        )

        return TestRunResult(
            passed=process.returncode == 0,
            failed_tests=failed_tests,
            new_failures=new_failures,
            regression_detected=regression_detected,
            targeted_tests=targeted_tests,
            targeted_command=targeted_command,
            targeted_exit_code=targeted_exit_code,
            output=combined_output,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            log_path=str(log_path),
            command=command,
        )

    def run(self, workflow_id: str, revision: int) -> TestRunOutcome:
        raise RuntimeError("Use run_repo_tests(repo_path, revision) in repo mode.")

    @staticmethod
    def _extract_failing_tests(output: str) -> list[str]:
        failed = re.findall(r"^FAILED\s+([^\s]+::[^\s]+)", output, flags=re.MULTILINE)
        if not failed:
            failed = re.findall(r"^([^\s]+::[^\s]+)\s+FAILED$", output, flags=re.MULTILINE)
        return sorted(set(failed))
