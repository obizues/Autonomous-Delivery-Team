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


# Always resolve project root as the folder containing 'src'
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
# Use .venv inside the autonomous_delivery directory
VENV_PYTHON = PROJECT_ROOT / "autonomous_delivery" / ".venv" / "Scripts" / "python.exe"
VENV_STREAMLIT = PROJECT_ROOT / "autonomous_delivery" / ".venv" / "Scripts" / "streamlit.exe"
# Correct APP path: project_root/autonomous_delivery/ui/app.py
APP = PROJECT_ROOT / "autonomous_delivery" / "ui" / "app.py"
DEFAULT_PORT = 8501
UI_SQLITE_PATH = "generated_workspace/asf_state_ui.db"


class WorkflowLauncher:
    """
    Encapsulates workflow and dashboard launching logic for maintainability and testability.
    """
    def __init__(self, args):
        self.args = args
        self.project_root = PROJECT_ROOT
        self.src_root = SRC_ROOT
        self.venv_python = VENV_PYTHON
        self.venv_streamlit = VENV_STREAMLIT
        self.app = APP
        self.default_port = 8501
        self.ui_sqlite_path = UI_SQLITE_PATH

    def _is_port_available(self, port: int) -> bool:
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

    def _select_dashboard_port(self, preferred: int, max_attempts: int = 20) -> int:
        for candidate in range(preferred, preferred + max_attempts):
            if self._is_port_available(candidate):
                return candidate
        raise RuntimeError(
            f"No available port found in range {preferred}-{preferred + max_attempts - 1}."
        )

    def run_workflow(self) -> None:
        print("\n[1/2] Running workflow engine...\n")
        print(f"[DEBUG] venv_python: {self.venv_python}")
        print(f"[DEBUG] project_root: {self.project_root}")
        print("[DEBUG] PYTHONPATH: src")
        if not self.venv_python.exists():
            print(
                f"\nERROR: Python executable not found at {self.venv_python}\n"
                "Did you create the virtual environment? Try: python -m venv .venv && .venv\\Scripts\\activate"
            )
            sys.exit(1)
        env = {
            **__import__("os").environ,
            "PYTHONPATH": "src",
            "ASF_SEED_REPO": self.args.seed_repo,
            "ASF_PERSISTENCE_BACKEND": "sqlite",
            "ASF_SQLITE_PATH": self.ui_sqlite_path,
        }
        if self.args.repo_url:
            env["ASF_REPO_URL"] = self.args.repo_url
        if self.args.repo_ref:
            env["ASF_REPO_REF"] = self.args.repo_ref
        try:
            result = subprocess.run(
                [str(self.venv_python), "-m", "autonomous_delivery.src.ai_software_factory"],
                cwd=self.project_root,
                env=env,
            )
        except FileNotFoundError as e:
            print(
                f"\nERROR: {e}\n[LAUNCHER] Could not find file. "
                "Check that all paths are correct and the virtual environment is set up."
            )
            sys.exit(1)
        if result.returncode != 0:
            print("\nERROR: Workflow engine failed.")
            sys.exit(result.returncode)

    def run_escalation_demo(self) -> None:
        print("\n[1/2] Running escalation demo...\n")
        result = subprocess.run(
            [str(self.venv_python), str(self.project_root / "scripts" / "demo_escalation.py")],
            cwd=self.project_root,
            env={
                **__import__("os").environ,
                "PYTHONPATH": "src",
            },
        )
        if result.returncode != 0:
            print("\nERROR: Escalation demo failed.")
            sys.exit(result.returncode)

    def launch_dashboard(self) -> None:
        preferred_port = self.args.port
        selected_port = self._select_dashboard_port(preferred_port)
        if selected_port != preferred_port:
            print(f"\nPort {preferred_port} is in use. Falling back to port {selected_port}.\n")
        print(
            f"\n[{('2/2' if not self.args.ui_only else '1/1')}] Starting dashboard at "
            f"http://localhost:{selected_port}\n"
        )
        env = {**__import__('os').environ, "PYTHONPATH": str(self.project_root)}
        try:
            result = subprocess.run(
                [
                    str(self.venv_streamlit),
                    "run", str(self.app),
                    f"--server.port={selected_port}",
                    "--server.headless=false",
                    "--browser.gatherUsageStats=false",
                ],
                cwd=self.project_root,
                env=env,
            )
        except KeyboardInterrupt:
            print("\nDashboard stopped by user.")
            return
        if result.returncode != 0:
            print(f"\nDashboard exited with code {result.returncode}.")


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


launcher = WorkflowLauncher(args)
if args.escalation_demo:
    launcher.run_escalation_demo()
elif not args.ui_only:
    launcher.run_workflow()
launcher.launch_dashboard()
