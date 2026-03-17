from __future__ import annotations

import shutil
from pathlib import Path


class RepoWorkspaceManager:
    def __init__(
        self,
        seed_repo_root: Path | None = None,
        sandbox_root: Path | None = None,
        seed_repo_name: str = "fake_upload_service",
    ) -> None:
        base = Path.cwd()
        self.seed_repo_name = seed_repo_name
        self.seed_repo_root = (seed_repo_root or (base / "seed_repos" / seed_repo_name)).resolve()
        self.sandbox_root = (sandbox_root or (base / "sandbox_repos")).resolve()

    def create_sandbox(self, workflow_id: str) -> Path:
        if not self.seed_repo_root.exists():
            raise FileNotFoundError(f"Seed repo not found: {self.seed_repo_root}")

        target = self.sandbox_root / f"run_{workflow_id}"
        if target.exists():
            return target

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.seed_repo_root, target)
        (target / "run_logs").mkdir(exist_ok=True)
        return target

    def ensure_sandbox(self, workflow_id: str) -> Path:
        target = self.sandbox_root / f"run_{workflow_id}"
        if target.exists():
            (target / "run_logs").mkdir(exist_ok=True)
            return target
        return self.create_sandbox(workflow_id)

    def sandbox_run_logs(self, workflow_id: str) -> Path:
        sandbox = self.ensure_sandbox(workflow_id)
        logs = sandbox / "run_logs"
        logs.mkdir(parents=True, exist_ok=True)
        return logs
