from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SQLITE_PATH = "generated_workspace/asf_state_resume_e2e.db"
_RESET_ENV_KEYS = {
    "ASF_RESUME_WORKFLOW_ID",
    "ASF_HUMAN_RESPONSE",
    "ASF_RESUME_STAGE",
    "ASF_RESUME_RESPONDER",
    "ASF_RESUME_MAX_STEPS",
    "ASF_FORCE_ESCALATION_DEMO",
}


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    return result.returncode, output


def _sanitized_env(base: dict[str, str]) -> dict[str, str]:
    clean = dict(base)
    for key in _RESET_ENV_KEYS:
        clean.pop(key, None)
    return clean


def _parse_readme(readme_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not readme_path.exists():
        return data
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- ") or ": " not in line:
            continue
        key, value = line[2:].split(": ", 1)
        data[key.strip()] = value.strip()
    return data


def _load_events(events_path: Path) -> list[dict]:
    if not events_path.exists():
        return []
    events: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    sqlite_file = root / SQLITE_PATH
    if sqlite_file.exists():
        sqlite_file.unlink()

    base_env = _sanitized_env({
        **os.environ,
        "PYTHONPATH": "src",
        "ASF_PERSISTENCE_BACKEND": "sqlite",
        "ASF_SQLITE_PATH": SQLITE_PATH,
    })

    print("[1/3] Running forced escalation scenario...")
    rc, out = _run(
        [str(python_exe), "-m", "ai_software_factory"],
        cwd=root,
        env={
            **base_env,
            "ASF_SEED_REPO": "fake_upload_service",
            "ASF_FORCE_ESCALATION_DEMO": "1",
        },
    )
    if rc != 0:
        print(out[-3000:])
        print("resume_e2e: FAILED (initial forced escalation run failed)")
        return 1

    latest = root / "demo_output" / "latest"
    summary = _parse_readme(latest / "README.md")
    workflow_id = summary.get("workflow_id", "")
    status = summary.get("final_status", "")
    if not workflow_id:
        print("resume_e2e: FAILED (missing workflow_id after forced escalation run)")
        return 1
    if status != "ESCALATED":
        print(f"resume_e2e: FAILED (expected ESCALATED, got {status or 'UNKNOWN'})")
        return 1

    print(f"[2/3] Resuming workflow {workflow_id} with policy controls...")
    rc, out = _run(
        [str(python_exe), "-m", "ai_software_factory"],
        cwd=root,
        env={
            **base_env,
            "ASF_RESUME_WORKFLOW_ID": workflow_id,
            "ASF_HUMAN_RESPONSE": "E2E resume test: continue from merge conflict gate with guarded retries.",
            "ASF_RESUME_STAGE": "MERGE_CONFLICT_GATE",
            "ASF_RESUME_RESPONDER": "qa_operator",
            "ASF_RESUME_MAX_STEPS": "150",
        },
    )
    if rc != 0:
        print(out[-3000:])
        print("resume_e2e: FAILED (resume run failed)")
        return 1

    print("[3/3] Validating resume events and artifacts...")
    summary_after = _parse_readme(latest / "README.md")
    events = _load_events(latest / "events.jsonl")

    final_status = summary_after.get("final_status", "")
    if final_status not in {"COMPLETED", "ESCALATED"}:
        print(f"resume_e2e: FAILED (unexpected final_status={final_status or 'UNKNOWN'})")
        return 1

    resumed = [
        event for event in events
        if event.get("event_type") == "WORKFLOW_RESUMED"
    ]
    if not resumed:
        print("resume_e2e: FAILED (WORKFLOW_RESUMED event not found)")
        return 1

    resumed_event = resumed[-1]
    resumed_stage = str(resumed_event.get("payload", {}).get("to_stage", ""))
    if resumed_stage != "MERGE_CONFLICT_GATE":
        print(f"resume_e2e: FAILED (expected resume to MERGE_CONFLICT_GATE, got {resumed_stage or 'UNKNOWN'})")
        return 1

    human_feedback = [
        event for event in events
        if event.get("event_type") == "HUMAN_FEEDBACK_RECORDED"
    ]
    if not human_feedback:
        print("resume_e2e: FAILED (HUMAN_FEEDBACK_RECORDED event not found)")
        return 1
    responder = str(human_feedback[-1].get("payload", {}).get("responder", ""))
    if responder != "qa_operator":
        print(f"resume_e2e: FAILED (expected responder qa_operator, got {responder or 'UNKNOWN'})")
        return 1

    revision_events = [
        event for event in events
        if event.get("event_type") == "REVISION_STARTED"
        and "Human intervention resume" in str(event.get("payload", {}).get("reason", ""))
    ]
    if not revision_events:
        print("resume_e2e: FAILED (resume REVISION_STARTED event not found)")
        return 1

    print(
        "resume_e2e: PASSED "
        f"(workflow_id={workflow_id}, final_status={final_status}, resume_stage={resumed_stage}, responder={responder})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
