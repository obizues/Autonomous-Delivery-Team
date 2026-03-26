from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse


class RepoWorkspaceManager:
    def push_to_remote(self, workflow_id: str, commit_message: str = None, branch: str = None) -> None:
        """
        Commit and push changes from the sandbox to the remote repository.
        Args:
            workflow_id: The workflow run identifier (sandbox folder).
            commit_message: Commit message to use. If None, a default is generated.
            branch: Branch to push to. If None, uses current branch.
        Raises:
            RuntimeError if git commands fail.
        """
        if not self.repo_url:
            raise RuntimeError("No remote repository URL configured for push.")
        sandbox = self.sandbox_root / f"run_{workflow_id}"
        if not sandbox.exists():
            raise FileNotFoundError(f"Sandbox not found: {sandbox}")

        # Stage all changes
        result = subprocess.run(["git", "add", "-A"], cwd=sandbox, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git add failed: {result.stderr or result.stdout}")

        # Commit
        if not commit_message:
            commit_message = f"Autonomous delivery commit for workflow {workflow_id}"
        result = subprocess.run(["git", "commit", "-m", commit_message], cwd=sandbox, capture_output=True, text=True)
        # Allow empty commit (no changes)
        if result.returncode not in (0, 1):
            raise RuntimeError(f"Git commit failed: {result.stderr or result.stdout}")

        # Optionally checkout branch
        if branch:
            result = subprocess.run(["git", "checkout", "-B", branch], cwd=sandbox, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Git checkout failed: {result.stderr or result.stdout}")

        # Push
        push_args = ["git", "push"]
        if branch:
            push_args += ["origin", branch]
        result = subprocess.run(push_args, cwd=sandbox, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git push failed: {result.stderr or result.stdout}")
    def __init__(
        self,
        seed_repo_root: Path | None = None,
        sandbox_root: Path | None = None,
        seed_repo_name: str = "fake_upload_service",
        repo_url: str | None = None,
        repo_ref: str | None = None,
    ) -> None:
        base = Path.cwd()
        self.repo_url = repo_url.strip() if repo_url else None
        self.repo_ref = repo_ref.strip() if repo_ref else None
        self.seed_repo_name = self._source_label(seed_repo_name)
        self.seed_repo_root = (seed_repo_root or (base / "seed_repos" / seed_repo_name)).resolve()
        self.sandbox_root = (sandbox_root or (base / "sandbox_repos")).resolve()

    def _source_label(self, seed_repo_name: str) -> str:
        if not self.repo_url:
            return seed_repo_name

        parsed = urlparse(self.repo_url)
        candidate = Path(parsed.path or self.repo_url).name.strip()
        if candidate.endswith(".git"):
            candidate = candidate[:-4]
        return candidate or self.repo_url

    def _clone_repo(self, target: Path) -> None:
        clone_command = ["git", "clone"]
        if not self.repo_ref:
            clone_command.extend(["--depth", "1"])
        clone_command.extend([self.repo_url or "", str(target)])

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(clone_command, capture_output=True, text=True)
            if result.returncode != 0:
                message = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
                raise RuntimeError(f"Git clone failed for {self.repo_url}: {message[-1000:]}")

            if self.repo_ref:
                checkout = subprocess.run(
                    ["git", "checkout", self.repo_ref],
                    cwd=target,
                    capture_output=True,
                    text=True,
                )
                if checkout.returncode != 0:
                    message = ((checkout.stderr or "") + "\n" + (checkout.stdout or "")).strip()
                    raise RuntimeError(f"Git checkout failed for ref '{self.repo_ref}': {message[-1000:]}")
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise

    def create_sandbox(self, workflow_id: str) -> Path:
        if not self.repo_url and not self.seed_repo_root.exists():
            raise FileNotFoundError(f"Seed repo not found: {self.seed_repo_root}")

        target = self.sandbox_root / f"run_{workflow_id}"
        if target.exists():
            return target

        target.parent.mkdir(parents=True, exist_ok=True)
        if self.repo_url:
            self._clone_repo(target)
        else:
            shutil.copytree(self.seed_repo_root, target)
        (target / "run_logs").mkdir(exist_ok=True)

        # Always copy the latest models.py from the seed repo to the sandbox src directory
        src_seed_models = self.seed_repo_root / "src" / "models.py"
        dst_sandbox_models = target / "src" / "models.py"
        if src_seed_models.exists():
            shutil.copy2(src_seed_models, dst_sandbox_models)

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
