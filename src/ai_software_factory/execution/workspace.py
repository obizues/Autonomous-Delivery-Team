from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class WorkspaceManager:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = (root_dir or (Path.cwd() / "generated_workspace")).resolve()

    def workflow_root(self, workflow_id: str) -> Path:
        return self.root_dir / workflow_id

    def ensure_workflow_workspace(self, workflow_id: str) -> Path:
        root = self.workflow_root(workflow_id)
        for relative in ("src", "tests", "run_logs", "revision_snapshots"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        return root

    def src_dir(self, workflow_id: str) -> Path:
        return self.ensure_workflow_workspace(workflow_id) / "src"

    def tests_dir(self, workflow_id: str) -> Path:
        return self.ensure_workflow_workspace(workflow_id) / "tests"

    def run_logs_dir(self, workflow_id: str) -> Path:
        return self.ensure_workflow_workspace(workflow_id) / "run_logs"

    def snapshot_revision(self, workflow_id: str, revision: int) -> Path:
        root = self.ensure_workflow_workspace(workflow_id)
        snapshots_root = root / "revision_snapshots"
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot = snapshots_root / f"rev_{revision}_{stamp}"
        snapshot.mkdir(parents=True, exist_ok=True)

        for relative in ("src", "tests"):
            source_path = root / relative
            if source_path.exists():
                shutil.copytree(source_path, snapshot / relative, dirs_exist_ok=True)
        return snapshot

    def list_workspace_files(self, workflow_id: str) -> list[str]:
        root = self.ensure_workflow_workspace(workflow_id)
        files: list[str] = []
        for relative in ("src", "tests"):
            base = root / relative
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.py")):
                files.append(path.relative_to(root).as_posix())
        return files
