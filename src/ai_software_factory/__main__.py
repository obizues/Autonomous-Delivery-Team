from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ai_software_factory.artifacts.markdown import render_artifact_markdown
from ai_software_factory.domain.enums import EventType, WorkflowStage, WorkflowStatus
from ai_software_factory.domain.models import CodeImplementation, TestResult
from ai_software_factory.orchestration.runner import build_demo_backlog, create_engine


def _to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_serializable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _to_serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_serializable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_serializable(item) for item in value]
    return value


class DemoOutputRecorder:
    def __init__(self, run_root: Path, append_existing: bool = False) -> None:
        self.run_root = run_root
        self.artifacts_dir = run_root / "artifacts"
        self.snapshots_dir = run_root / "state_snapshots"
        self.events_log_path = run_root / "events.jsonl"
        self.summary_path = run_root / "README.md"
        self._written_artifact_ids: set[str] = set()
        self._written_event_ids: set[str] = set()
        self._step = 0

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        if append_existing:
            self._written_artifact_ids = {
                file_path.stem.split("_")[0]
                for file_path in self.artifacts_dir.glob("*.json")
            }
            if self.events_log_path.exists():
                for line in self.events_log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        event_id = str(json.loads(line).get("event_id", ""))
                    except json.JSONDecodeError:
                        continue
                    if event_id:
                        self._written_event_ids.add(event_id)
            existing_steps = []
            for file_path in self.snapshots_dir.glob("step_*.json"):
                prefix = file_path.stem.split("_", 2)[1] if "_" in file_path.stem else "0"
                try:
                    existing_steps.append(int(prefix))
                except ValueError:
                    continue
            self._step = max(existing_steps, default=0)
        elif self.events_log_path.exists():
            self.events_log_path.unlink()

    def record_artifacts_from_events(self, engine: Any, workflow_id: str, events: list[Any]) -> list[str]:
        """Persist JSON + Markdown for each new artifact. Returns list of markdown filenames written."""
        written_md: list[str] = []
        for event in events:
            if event.event_type != EventType.ARTIFACT_CREATED:
                continue
            artifact_id = str(event.payload.get("artifact_id", ""))
            artifact_type = str(event.payload.get("artifact_type", "Artifact"))
            if not artifact_id or artifact_id in self._written_artifact_ids:
                continue

            artifact = engine.artifact_store.get(artifact_id)
            if artifact is None:
                continue

            json_path = self.artifacts_dir / f"{artifact_id}_{artifact_type}.json"
            json_path.write_text(
                json.dumps(_to_serializable(artifact), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            rendered = render_artifact_markdown(artifact)
            if rendered is not None:
                slug, content = rendered
                md_path = self.artifacts_dir / f"{artifact_id}_{slug}.md"
                md_path.write_text(content, encoding="utf-8")
                written_md.append(md_path.name)

            self._written_artifact_ids.add(artifact_id)
        return written_md

    def record_state_snapshot(self, state: Any, stage_name: str) -> None:
        self._step += 1
        snapshot_path = self.snapshots_dir / f"step_{self._step:03d}_{stage_name}.json"
        snapshot_path.write_text(
            json.dumps(_to_serializable(state), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def append_events(self, events: list[Any]) -> None:
        with self.events_log_path.open("a", encoding="utf-8") as file_handle:
            for event in events:
                if event.event_id in self._written_event_ids:
                    continue
                file_handle.write(
                    json.dumps(
                        {
                            "event_id": event.event_id,
                            "timestamp": event.timestamp.isoformat(),
                            "event_type": event.event_type.value,
                            "stage": event.stage.value,
                            "payload": _to_serializable(event.payload),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                self._written_event_ids.add(event.event_id)

    def write_summary(
        self,
        state: Any,
        latest_output_path: Path,
        execution_summary: dict[str, Any],
        seed_repo_name: str,
        scenario_title: str,
    ) -> None:
        summary = [
            "# AI Software Factory Demo Output",
            "",
            f"- workflow_id: {state.workflow_id}",
            f"- final_status: {state.status.value}",
            f"- final_stage: {state.current_stage.value}",
            f"- revision_count: {state.revision}",
            f"- seed_repo_name: {seed_repo_name}",
            f"- scenario_title: {scenario_title}",
            f"- latest_output_path: {latest_output_path}",
            f"- artifacts: {len(state.artifact_ids)}",
            f"- approvals: {len(state.approval_ids)}",
            f"- reviews: {len(state.review_feedback_ids)}",
            f"- generated_workspace_path: {execution_summary.get('workspace_path', 'N/A')}",
            f"- sandbox_repo_path: {execution_summary.get('workspace_path', 'N/A')}",
            f"- generated_source_files: {execution_summary.get('source_files_count', 0)}",
            f"- generated_test_files: {execution_summary.get('test_files_count', 0)}",
            f"- last_pytest_passed: {execution_summary.get('last_test_passed', 'N/A')}",
            f"- last_pytest_log: {execution_summary.get('last_test_log', 'N/A')}",
            "",
            "## Contents",
            "",
            "- `artifacts/`: one JSON file per produced artifact",
            "- `state_snapshots/`: workflow state snapshot after each stage",
            "- `events.jsonl`: chronological event stream",
            "- `demo_output/latest`: stable path to most recent run",
        ]
        self.summary_path.write_text("\n".join(summary), encoding="utf-8")


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _update_latest_output_alias(demo_output_root: Path, run_root: Path) -> tuple[Path, str]:
    latest_path = demo_output_root / "latest"
    _remove_path(latest_path)

    try:
        latest_path.symlink_to(run_root, target_is_directory=True)
        return latest_path, "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(run_root, latest_path)
        return latest_path, "copy"


def main() -> None:
    selected_seed_repo = os.getenv("ASF_SEED_REPO", "fake_upload_service")
    selected_repo_url = os.getenv("ASF_REPO_URL")
    selected_repo_ref = os.getenv("ASF_REPO_REF")
    resume_workflow_id = os.getenv("ASF_RESUME_WORKFLOW_ID")
    human_response = os.getenv("ASF_HUMAN_RESPONSE", "")
    repo_source = selected_repo_url or selected_seed_repo
    engine = create_engine(
        seed_repo_name=selected_seed_repo,
        repo_url=selected_repo_url,
        repo_ref=selected_repo_ref,
    )

    if resume_workflow_id:
        existing_artifacts = engine.artifact_store.list_by_workflow(resume_workflow_id)
        backlog_item = next((artifact for artifact in existing_artifacts if artifact.__class__.__name__ == "BacklogItem"), None)
        if backlog_item is None:
            backlog_item = build_demo_backlog(selected_seed_repo, repo_url=selected_repo_url)
            backlog_item.title = f"Resumed workflow {resume_workflow_id}"
        state = engine.resume_from_escalation(
            workflow_id=resume_workflow_id,
            human_response=human_response,
        )
    else:
        backlog_item = build_demo_backlog(selected_seed_repo, repo_url=selected_repo_url)
        state = engine.start(backlog_item)

    workflow_id = state.workflow_id
    demo_output_root = Path.cwd() / "demo_output"
    output_root = demo_output_root / workflow_id
    recorder = DemoOutputRecorder(output_root, append_existing=bool(resume_workflow_id))
    event_index = 0
    print(f"Workflow started: {workflow_id}")
    print(f"Repo source: {repo_source}")
    if selected_repo_ref:
        print(f"Repo ref: {selected_repo_ref}")
    if resume_workflow_id:
        print("Resume mode: applying human intervention and continuing workflow")
        print(f"Human response: {human_response}")
    print(f"Backlog item: {backlog_item.title}")
    print(f"Demo output directory: {output_root}")
    print("-" * 72)

    startup_events = engine.event_bus.list_events(workflow_id)
    recorder.append_events(startup_events)
    written_md = recorder.record_artifacts_from_events(engine, workflow_id, startup_events)
    for md_name in written_md:
        print(f"  Markdown artifact: {md_name}")
    recorder.record_state_snapshot(state, "START")
    event_index = len(startup_events)

    while True:
        state = engine.state_store.load(workflow_id)
        if state.status != WorkflowStatus.IN_PROGRESS:
            break
        if state.current_stage == WorkflowStage.DONE:
            engine.execute_next(workflow_id)
            state = engine.state_store.load(workflow_id)
            break

        previous_stage = state.current_stage
        previous_revision = state.revision

        engine.execute_next(workflow_id)
        state = engine.state_store.load(workflow_id)

        print(f"Stage transition: {previous_stage.value} -> {state.current_stage.value}")

        events = engine.event_bus.list_events(workflow_id)
        new_events = events[event_index:]
        event_index = len(events)

        recorder.append_events(new_events)
        written_md = recorder.record_artifacts_from_events(engine, workflow_id, new_events)
        recorder.record_state_snapshot(state, previous_stage.value)

        for event in new_events:
            if event.event_type == EventType.ARTIFACT_CREATED:
                artifact_type = str(event.payload.get("artifact_type", "UnknownArtifact"))
                artifact_id = str(event.payload.get("artifact_id", "unknown"))
                print(f"  Artifact produced: {artifact_type} ({artifact_id[:8]}…)")
            elif event.event_type == EventType.STAGE_STARTED:
                print(f"  Event: stage started ({event.stage.value})")
            elif event.event_type == EventType.APPROVAL_RECORDED:
                decision = str(event.payload.get("decision", "UNKNOWN"))
                print(f"  Review decision: {decision}")
            elif event.event_type == EventType.DECISION_MADE:
                decision = str(event.payload.get("decision", "UNKNOWN"))
                print(f"  Event: decision made ({decision})")
            elif event.event_type == EventType.TRANSITION_OCCURRED:
                from_stage = str(event.payload.get("from_stage", "UNKNOWN"))
                to_stage = str(event.payload.get("to_stage", "UNKNOWN"))
                print(f"  Event: transition occurred ({from_stage} -> {to_stage})")
            elif event.event_type == EventType.REVISION_STARTED:
                new_revision = str(event.payload.get("new_revision", state.revision))
                print(f"  Revision loop: REQUEST_CHANGES -> IMPLEMENTATION (revision {new_revision})")
            elif event.event_type == EventType.REPO_SCANNED:
                scanned = int(event.payload.get("python_files", 0))
                sandbox_path = str(event.payload.get("sandbox_path", "N/A"))
                print(f"  Repo scanned: {scanned} python files")
                print(f"  Sandbox path: {sandbox_path}")
            elif event.event_type == EventType.CHANGE_PLAN_GENERATED:
                summary = str(event.payload.get("summary", "Plan generated"))
                print(f"  Change plan generated: {summary}")
            elif event.event_type == EventType.FILES_MODIFIED:
                files_changed = event.payload.get("files_changed", [])
                print(f"  Files modified: {', '.join(files_changed) if files_changed else 'none'}")
            elif event.event_type == EventType.TEST_EXECUTION_STARTED:
                print("  Test execution: started")
            elif event.event_type == EventType.TEST_EXECUTION_COMPLETED:
                passed = bool(event.payload.get("passed", False))
                exit_code = str(event.payload.get("exit_code", "?"))
                log_path = str(event.payload.get("log_path", "N/A"))
                print(f"  Test execution: completed (passed={passed}, exit_code={exit_code})")
                print(f"  Test run log: {log_path}")
            elif event.event_type == EventType.TEST_FAILED:
                failing = event.payload.get("failing_tests", [])
                print(f"  Test execution: FAILED ({len(failing)} failing tests)")
            elif event.event_type == EventType.TEST_PASSED:
                print("  Test execution: PASSED")

        for md_name in written_md:
            print(f"  Markdown artifact: {md_name}")

        if state.revision > previous_revision:
            print(f"  Revision incremented: {previous_revision} -> {state.revision}")

        print("-" * 72)

    final_state = engine.state_store.load(workflow_id)

    workflow_artifacts = engine.artifact_store.list_by_workflow(workflow_id)
    latest_implementation = next(
        (artifact for artifact in reversed(workflow_artifacts) if isinstance(artifact, CodeImplementation)),
        None,
    )
    latest_test_result = next(
        (artifact for artifact in reversed(workflow_artifacts) if isinstance(artifact, TestResult)),
        None,
    )

    execution_summary = {
        "workspace_path": latest_implementation.workspace_path if latest_implementation else "N/A",
        "source_files_count": len(latest_implementation.written_source_files) if latest_implementation else 0,
        "test_files_count": len(latest_test_result.generated_test_files) if latest_test_result else 0,
        "last_test_passed": latest_test_result.passed if latest_test_result else "N/A",
        "last_test_log": latest_test_result.run_log_path if latest_test_result else "N/A",
    }

    print("Workflow complete")
    print(f"Final status: {final_state.status.value}")
    print(f"Final stage: {final_state.current_stage.value}")
    print(f"Final revision: {final_state.revision}")
    print(f"Generated workspace path: {execution_summary['workspace_path']}")
    print(f"Generated source files: {execution_summary['source_files_count']}")
    print(f"Generated test files: {execution_summary['test_files_count']}")
    print(f"Last pytest passed: {execution_summary['last_test_passed']}")
    print(f"Last pytest log: {execution_summary['last_test_log']}")
    latest_output_path = demo_output_root / "latest"
    recorder.write_summary(
        final_state,
        latest_output_path=latest_output_path,
        execution_summary=execution_summary,
        seed_repo_name=repo_source,
        scenario_title=backlog_item.title,
    )
    latest_path, latest_mode = _update_latest_output_alias(demo_output_root=demo_output_root, run_root=output_root)
    print(f"Output saved to: {output_root}")
    print(f"Latest output ({latest_mode}): {latest_path}")


if __name__ == "__main__":
    main()
