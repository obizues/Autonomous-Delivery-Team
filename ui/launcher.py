"""
Launcher for the AI Software Factory dashboard.

Usage:
    python ui/launcher.py            # run workflow then open dashboard
    python ui/launcher.py --ui-only  # skip workflow, just open dashboard
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_STREAMLIT = ROOT / ".venv" / "Scripts" / "streamlit.exe"
APP = ROOT / "ui" / "app.py"
PORT = 8501


def run_workflow() -> None:
    print("\n[1/2] Running workflow engine...\n")
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "ai_software_factory"],
        cwd=ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": "src",
            "ASF_SEED_REPO": args.seed_repo,
        },
    )
    if result.returncode != 0:
        print("\nERROR: Workflow engine failed.")
        sys.exit(result.returncode)


def launch_dashboard() -> None:
    print(f"\n[{'2/2' if not args.ui_only else '1/1'}] Starting dashboard at http://localhost:{PORT}\n")
    webbrowser.open(f"http://localhost:{PORT}")
    subprocess.run(
        [
            str(VENV_STREAMLIT),
            "run", str(APP),
            f"--server.port={PORT}",
            "--server.headless=false",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
    )


parser = argparse.ArgumentParser(description="AI Software Factory launcher")
parser.add_argument("--ui-only", action="store_true", help="Skip workflow run, open dashboard directly")
parser.add_argument(
    "--seed-repo",
    default="fake_upload_service",
    choices=["fake_upload_service", "simple_auth_service", "data_pipeline"],
    help="Seed repo scenario to run before opening dashboard",
)
args = parser.parse_args()

if not args.ui_only:
    run_workflow()

launch_dashboard()
