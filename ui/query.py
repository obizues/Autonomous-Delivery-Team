"""
Pure-Python query helpers: no Streamlit imports, no I/O.
Operate only on already-loaded data structures.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from config import ARTIFACT_TYPE_LABELS, STAGE_META, STAGE_ORDER


# ── Formatting ────────────────────────────────────────────────────────────────


def decision_badge(decision: str) -> str:
    cls = {
        "APPROVED":        "badge-approved",
        "REQUEST_CHANGES": "badge-changes",
        "REJECT":          "badge-reject",
    }.get(decision, "badge-completed")
    label = decision.replace("_", " ")
    return f'<span class="badge {cls}">{label}</span>'


# ── Event / artifact indexing ─────────────────────────────────────────────────


def stage_decisions(events: list[dict]) -> dict[str, list[str]]:
    """Map stage → list of decision strings from DECISION_MADE events."""
    result: dict[str, list[str]] = defaultdict(list)
    for evt in events:
        if evt.get("event_type") == "DECISION_MADE":
            p = evt.get("payload", {})
            stage = evt.get("stage", "") or p.get("stage", "")
            decision = p.get("decision", "")
            if stage and decision:
                result[stage].append(decision)
    return dict(result)


def artifacts_by_stage(artifacts: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for a in artifacts:
        result[a["stage"]].append(a)
    return dict(result)


def get_backlog_title(artifacts: list[dict]) -> str:
    for a in artifacts:
        if a["type"] == "BacklogItem":
            return a["meta"].get("title", "Untitled")
    return "Untitled"


def get_backlog_problem(artifacts: list[dict]) -> str:
    for a in artifacts:
        if a["type"] == "BacklogItem":
            return a["meta"].get("problem_statement", "")
    return ""


def count_decisions(events: list[dict], decision: str) -> int:
    return sum(
        1 for e in events
        if e.get("event_type") == "DECISION_MADE"
        and e.get("payload", {}).get("decision") == decision
    )


def latest_artifact(
    artifacts: list[dict],
    artifact_type: str,
    stage: str | None = None,
) -> dict | None:
    matches = [
        a for a in artifacts
        if a.get("type") == artifact_type
        and (stage is None or a.get("stage") == stage)
    ]
    if not matches:
        return None

    def _key(a: dict) -> tuple[int, str, str]:
        return (
            int(a.get("version", 1) or 1),
            str(a.get("meta", {}).get("created_at", "")),
            str(a.get("meta", {}).get("artifact_id", a.get("uuid", ""))),
        )

    return max(matches, key=_key)


def first_artifact(
    artifacts: list[dict],
    stage: str,
    version: int,
    artifact_type: str,
) -> dict | None:
    for a in artifacts:
        if (
            a.get("stage") == stage
            and int(a.get("version", 1)) == version
            and a.get("type") == artifact_type
        ):
            return a
    return None


def list_added(previous_items: list[str], next_items: list[str]) -> list[str]:
    previous_set = set(previous_items)
    return [item for item in next_items if item not in previous_set]


def latest_snapshot(snapshots: dict[str, list[dict]]) -> dict:
    newest: dict = {}
    newest_step = -1
    for stage_items in snapshots.values():
        for item in stage_items:
            filename = item.get("_filename", "")
            match = re.search(r"step_(\d+)_", filename)
            step = int(match.group(1)) if match else -1
            if step > newest_step:
                newest_step = step
                newest = item
    return newest


def effective_workflow_status(
    readme: dict[str, str],
    events: list[dict[str, Any]],
    snapshots: dict[str, list[dict]],
) -> str:
    readme_status = str(readme.get("final_status", "") or "").upper()
    latest = latest_snapshot(snapshots)
    snapshot_status = str(latest.get("status", "") or "").upper()
    final_stage = str(readme.get("final_stage", latest.get("current_stage", "")) or "").upper()

    for candidate in (readme_status, snapshot_status):
        if candidate in {"COMPLETED", "FAILED", "ESCALATED"}:
            return candidate

    if final_stage == "DONE":
        if any(event.get("event_type") == "ESCALATION_RAISED" for event in events):
            return "ESCALATED"
        return "COMPLETED"

    if readme_status:
        return readme_status
    if snapshot_status:
        return snapshot_status
    return "UNKNOWN"


def detect_active_context(artifacts: list[dict], events: list[dict]) -> dict[str, str]:
    backlog = latest_artifact(artifacts, "BacklogItem", "BACKLOG_INTAKE")
    latest_scan = None
    for event in reversed(events):
        if event.get("event_type") == "REPO_SCANNED":
            latest_scan = event
            break

    seed_repo_name = "unknown"
    sandbox_path = "N/A"

    if latest_scan:
        payload = latest_scan.get("payload", {})
        seed_repo_name = str(payload.get("seed_repo_name", "unknown"))
        sandbox_path = str(payload.get("sandbox_path", "N/A"))

    latest_impl = latest_artifact(artifacts, "CodeImplementation", "IMPLEMENTATION")
    repo_profile = "unknown"
    if latest_impl:
        for note in latest_impl.get("meta", {}).get("implementation_notes", []):
            if note.startswith("Detected repo profile: "):
                repo_profile = note.split(": ", 1)[1].strip()
            if note.startswith("Seed repo: ") and seed_repo_name == "unknown":
                seed_repo_name = note.split(": ", 1)[1].strip()
            if note.startswith("Repo source: ") and seed_repo_name == "unknown":
                seed_repo_name = note.split(": ", 1)[1].strip()

    title = backlog.get("meta", {}).get("title", "Active backlog") if backlog else "Active backlog"
    problem = backlog.get("meta", {}).get("problem_statement", "") if backlog else ""

    return {
        "seed_repo_name": seed_repo_name,
        "repo_profile": repo_profile,
        "scenario_title": title,
        "problem_statement": problem,
        "sandbox_path": sandbox_path,
    }


def team_overview(snapshots: dict[str, list[dict]]) -> list[dict[str, str | int]]:
    role_order = [
        "Product Owner",
        "Business Analyst",
        "Architect",
        "Engineer",
        "Test Engineer",
    ]
    rows: list[dict[str, str | int]] = []

    role_aliases: dict[str, set[str]] = {
        "Engineer": {"Engineer", "Engineer Team", "Engineer Agents"},
    }

    def _matches_role(stage_role: str, role: str) -> bool:
        if stage_role == role:
            return True
        return stage_role in role_aliases.get(role, set())

    for role in role_order:
        role_stages = [
            stage for stage in STAGE_ORDER
            if _matches_role(STAGE_META.get(stage, ("", "", ""))[2], role)
        ]
        role_revisions: set[int] = set()
        stage_executions = 0
        for stage in role_stages:
            for snap in snapshots.get(stage, []):
                stage_executions += 1
                revision = snap.get("revision")
                if isinstance(revision, int):
                    role_revisions.add(revision)

        revision_span = len(role_revisions)
        last_stage = "—"
        for stage in reversed(STAGE_ORDER):
            if stage in role_stages and snapshots.get(stage):
                last_stage = STAGE_META.get(stage, ("", stage, ""))[1]
                break

        status = "Not active"
        if stage_executions > 0:
            status = "Completed" if revision_span <= 1 else f"Worked across {revision_span} revisions"

        rows.append({
            "role": role,
            "status": status,
            "cycles": revision_span,
            "last_stage": last_stage,
        })
    return rows
