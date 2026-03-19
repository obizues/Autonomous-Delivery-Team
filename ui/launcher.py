"""
Launcher for the AI Software Factory dashboard.

Usage:
    python ui/launcher.py            # run workflow then open dashboard
    python ui/launcher.py --ui-only  # skip workflow, just open dashboard
    python ui/launcher.py --escalation-demo  # run escalation demo then open dashboard
    python ui/launcher.py --port 8600  # prefer port 8600, fallback if unavailable
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_STREAMLIT = ROOT / ".venv" / "Scripts" / "streamlit.exe"
APP = ROOT / "ui" / "app.py"
DEFAULT_PORT = 8501
UI_SQLITE_PATH = "generated_workspace/asf_state_ui.db"


def _is_port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ipv4_sock:
            ipv4_sock.bind(("0.0.0.0", port))
    except OSError:
        return False

    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as ipv6_sock:
            ipv6_sock.bind(("::", port))
    except OSError:
        pass

    return True


def _select_dashboard_port(preferred: int, max_attempts: int = 20) -> int:
    for candidate in range(preferred, preferred + max_attempts):
        if _is_port_available(candidate):
            return candidate
    raise RuntimeError(
        f"No available port found in range {preferred}-{preferred + max_attempts - 1}."
    )


def run_workflow() -> None:
    print("\n[1/2] Running workflow engine...\n")
    env = {
        **__import__("os").environ,
        "PYTHONPATH": "src",
        "ASF_SEED_REPO": args.seed_repo,
        "ASF_PERSISTENCE_BACKEND": "sqlite",
        "ASF_SQLITE_PATH": UI_SQLITE_PATH,
    }
    if args.repo_url:
        env["ASF_REPO_URL"] = args.repo_url
    if args.repo_ref:
        env["ASF_REPO_REF"] = args.repo_ref

    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "ai_software_factory"],
        cwd=ROOT,
        env=env,
    )
    if result.returncode != 0:
        print("\nERROR: Workflow engine failed.")
        sys.exit(result.returncode)


def run_escalation_demo() -> None:
    print("\n[1/2] Running escalation demo...\n")
    result = subprocess.run(
        [str(VENV_PYTHON), "scripts/demo_escalation.py"],
        cwd=ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": "src",
        },
    )
    if result.returncode != 0:
        print("\nERROR: Escalation demo failed.")
        sys.exit(result.returncode)


def launch_dashboard() -> None:
    preferred_port = args.port
    selected_port = _select_dashboard_port(preferred_port)
    if selected_port != preferred_port:
        print(f"\nPort {preferred_port} is in use. Falling back to port {selected_port}.\n")

    print(
        f"\n[{'2/2' if not args.ui_only else '1/1'}] Starting dashboard at "
        f"http://localhost:{selected_port}\n"
    )
    subprocess.run(
        [
            str(VENV_STREAMLIT),
            "run", str(APP),
            f"--server.port={selected_port}",
            "--server.headless=false",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
    )


parser = argparse.ArgumentParser(description="AI Software Factory launcher")
parser.add_argument("--ui-only", action="store_true", help="Skip workflow run, open dashboard directly")
parser.add_argument("--escalation-demo", action="store_true", help="Run escalation demo before opening dashboard")
parser.add_argument(
    "--port",
    type=int,
    default=DEFAULT_PORT,
    help="Preferred dashboard port (launcher auto-falls back if unavailable)",
)
parser.add_argument(
    "--seed-repo",
    default="fake_upload_service",
    choices=["fake_upload_service", "simple_auth_service", "data_pipeline"],
    help="Seed repo scenario to run before opening dashboard",
)
parser.add_argument("--repo-url", default=None, help="Optional Git repository URL to clone instead of a seed repo")
parser.add_argument("--repo-ref", default=None, help="Optional Git branch, tag, or commit to checkout after clone")
args = parser.parse_args()

if args.escalation_demo:
    run_escalation_demo()
elif not args.ui_only:
    run_workflow()

launch_dashboard()
