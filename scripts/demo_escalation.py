from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

UI_SQLITE_PATH = "generated_workspace/asf_state_ui.db"

def _safe_console_text(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding, errors="replace")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    process = subprocess.run(
        [str(python_exe), "-m", "ai_software_factory"],
        cwd=root,
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "ASF_SEED_REPO": "fake_upload_service",
            "ASF_FORCE_ESCALATION_DEMO": "1",
            "ASF_PERSISTENCE_BACKEND": "sqlite",
            "ASF_SQLITE_PATH": UI_SQLITE_PATH,
        },
        capture_output=True,
        text=True,
    )

    output = ((process.stdout or "") + "\n" + (process.stderr or "")).strip()
    if process.returncode != 0:
        print(_safe_console_text(output[-3000:] if output else "Escalation demo run failed with no output."))
        return process.returncode

    latest_dir = root / "demo_output" / "latest"
    readme_path = latest_dir / "README.md"
    events_path = latest_dir / "events.jsonl"

    summary: dict[str, str] = {}
    if readme_path.exists():
        for line in readme_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("- ") or ": " not in line:
                continue
            key, value = line[2:].split(": ", 1)
            summary[key.strip()] = value.strip()

    escalation_count = 0
    escalation_reason = "N/A"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event_type") == "ESCALATION_RAISED":
                escalation_count += 1
                escalation_reason = str(event.get("payload", {}).get("reason", escalation_reason))

    print(f"workflow_id: {summary.get('workflow_id', 'N/A')}")
    print(f"status: {summary.get('final_status', 'N/A')}")
    print(f"stage: {summary.get('final_stage', 'N/A')}")
    print(f"revision: {summary.get('revision_count', 'N/A')}")
    print("forced_escalation_demo: True")
    print(f"escalation_events: {escalation_count}")
    print(f"escalation_reason: {_safe_console_text(escalation_reason)}")

    if summary.get("final_status") != "ESCALATED" or escalation_count == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
