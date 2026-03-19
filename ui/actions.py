"""
Dashboard action runners: subprocess calls back into the workflow engine.
"""
from __future__ import annotations

import os
import subprocess
import sys

from config import BASE_DIR, UI_SQLITE_PATH


def run_workflow_from_dashboard(
    seed_repo_name: str,
    repo_url: str | None = None,
    repo_ref: str | None = None,
) -> tuple[bool, str]:
    try:
        env = {
            **os.environ,
            "PYTHONPATH": "src",
            "ASF_SEED_REPO": seed_repo_name,
            "ASF_PERSISTENCE_BACKEND": "sqlite",
            "ASF_SQLITE_PATH": UI_SQLITE_PATH,
        }
        if repo_url:
            env["ASF_REPO_URL"] = repo_url
        if repo_ref:
            env["ASF_REPO_REF"] = repo_ref

        result = subprocess.run(
            [sys.executable, "-m", "ai_software_factory"],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to run workflow: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Workflow failed with no output."
    return True, output[-4000:] if output else "Workflow completed successfully."


def run_escalation_demo_from_dashboard() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/demo_escalation.py"],
            cwd=BASE_DIR,
            env={
                **os.environ,
                "PYTHONPATH": "src",
                "ASF_PERSISTENCE_BACKEND": "sqlite",
                "ASF_SQLITE_PATH": UI_SQLITE_PATH,
            },
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to run escalation demo: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Escalation demo failed with no output."
    return True, output[-4000:] if output else "Escalation demo completed successfully."


def run_resume_from_dashboard(
    workflow_id: str,
    human_response: str,
    resume_stage: str = "IMPLEMENTATION",
    responder: str = "human_operator",
    resume_max_steps: int = 120,
) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ai_software_factory"],
            cwd=BASE_DIR,
            env={
                **os.environ,
                "PYTHONPATH": "src",
                "ASF_PERSISTENCE_BACKEND": "sqlite",
                "ASF_SQLITE_PATH": UI_SQLITE_PATH,
                "ASF_RESUME_WORKFLOW_ID": workflow_id,
                "ASF_HUMAN_RESPONSE": human_response,
                "ASF_RESUME_STAGE": resume_stage,
                "ASF_RESUME_RESPONDER": responder,
                "ASF_RESUME_MAX_STEPS": str(resume_max_steps),
            },
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to resume workflow: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Workflow resume failed with no output."
    return True, output[-4000:] if output else "Workflow resumed successfully."


def latest_escalation_reason(events: list[dict]) -> str | None:
    for event in reversed(events):
        if event.get("event_type") != "ESCALATION_RAISED":
            continue
        payload = event.get("payload", {})
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None
