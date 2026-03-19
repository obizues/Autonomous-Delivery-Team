"""
AI Software Factory — Streamlit Dashboard
Run with:
  streamlit run ui/app.py
from the autonomous_delivery directory.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import streamlit as st

# ── Constants ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DEMO_OUTPUT = BASE_DIR / "demo_output" / "latest"

STAGE_ORDER = [
    "BACKLOG_INTAKE",
    "PRODUCT_DEFINITION",
    "REQUIREMENTS_ANALYSIS",
    "ARCHITECTURE_DESIGN",
    "IMPLEMENTATION",
    "PULL_REQUEST_CREATED",
    "ARCHITECTURE_REVIEW_GATE",
    "PEER_CODE_REVIEW_GATE",
    "TEST_VALIDATION_GATE",
    "PRODUCT_ACCEPTANCE_GATE",
    "DONE",
]

STAGE_META: dict[str, tuple[str, str, str]] = {
    "BACKLOG_INTAKE":           ("📋", "Backlog Intake",          "Product Owner"),
    "PRODUCT_DEFINITION":       ("📝", "Product Definition",       "Product Owner"),
    "REQUIREMENTS_ANALYSIS":    ("🔍", "Requirements Analysis",    "Business Analyst"),
    "ARCHITECTURE_DESIGN":      ("🏗️", "Architecture Design",      "Architect"),
    "IMPLEMENTATION":           ("💻", "Implementation",           "Engineer"),
    "PULL_REQUEST_CREATED":     ("🔀", "Pull Request",             "Engineer"),
    "ARCHITECTURE_REVIEW_GATE": ("🏛️", "Architecture Review",     "Architect"),
    "PEER_CODE_REVIEW_GATE":    ("👥", "Peer Code Review",         "Engineer"),
    "TEST_VALIDATION_GATE":     ("🧪", "Test Validation",          "Test Engineer"),
    "PRODUCT_ACCEPTANCE_GATE":  ("✅", "Product Acceptance",        "Product Owner"),
    "DONE":                     ("🎉", "Done",                     "—"),
}

REVIEW_GATES = {
    "ARCHITECTURE_REVIEW_GATE",
    "PEER_CODE_REVIEW_GATE",
    "TEST_VALIDATION_GATE",
    "PRODUCT_ACCEPTANCE_GATE",
}

ARTIFACT_TYPE_LABELS = {
    "BacklogItem":        "Backlog Item",
    "RequirementsSpec":   "Requirements Spec",
    "ArchitectureSpec":   "Architecture Design",
    "CodeImplementation": "Implementation Plan",
    "EscalationArtifact": "Workflow Escalation",
    "HumanIntervention":  "Human Intervention",
    "PullRequest":        "Pull Request",
    "ReviewFeedback":     "Review Feedback",
    "TestResult":         "Test Report",
}

EVENT_ICONS = {
    "WORKFLOW_STARTED":    "🚀",
    "STAGE_STARTED":       "▶️",
    "STAGE_COMPLETED":     "✅",
    "ARTIFACT_CREATED":    "📄",
    "DECISION_MADE":       "⚖️",
    "TRANSITION_OCCURRED": "➡️",
    "APPROVAL_RECORDED":   "✔️",
    "ESCALATION_RAISED":   "⚠️",
    "REVISION_STARTED":    "🔄",
    "REPO_SCANNED": "🗂️",
    "CHANGE_PLAN_GENERATED": "🧭",
    "FILES_MODIFIED": "🛠️",
    "PATCH_APPLIED": "🧩",
    "PATCH_ROLLED_BACK": "↩️",
    "TEST_EXECUTION_STARTED": "🧪",
    "TEST_EXECUTION_COMPLETED": "📋",
    "TEST_PASSED": "✅",
    "TEST_FAILED": "❌",
    "HUMAN_FEEDBACK_RECORDED": "🧑‍💼",
    "ESCALATION_RESOLVED": "🟢",
    "WORKFLOW_RESUMED": "🔁",
    "WORKFLOW_COMPLETED":  "🏁",
}

UI_SQLITE_PATH = "generated_workspace/asf_state_ui.db"

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Software Factory",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

_tokens = {
    "app_bg": "#f3f6fb",
    "sidebar_bg": "#ffffff",
    "text_primary": "#0b1220",
    "text_secondary": "#1f2937",
    "text_muted": "#334155",
    "code_fg": "#1e40af",
    "code_bg": "#e0ecff",
    "surface": "#ffffff",
    "surface_alt": "#f1f5f9",
    "border": "#94a3b8",
    "hover": "#dbe7f5",
    "chip_bg": "#ffffff",
    "wf_current_bg": "#dbeafe",
    "wf_loop_bg": "#fff7ed",
}

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ font-size: 15px !important; }}

    [data-testid="stAppViewContainer"] {{ background: {_tokens['app_bg']}; }}
    [data-testid="stHeader"] {{ background: transparent; }}

    [data-testid="stSidebar"] {{ background: {_tokens['sidebar_bg']}; min-width: 260px; }}
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] .sidebar-title {{ color: {_tokens['text_primary']}; font-size: 1.15rem !important; font-weight: 700; }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {{ color: {_tokens['text_secondary']} !important; }}
    [data-testid="stSidebar"] code {{ font-size: 0.85rem !important; color: {_tokens['code_fg']} !important; background: {_tokens['code_bg']}; }}

    [data-testid="stMetric"] label {{ font-size: 0.9rem !important; color: {_tokens['text_muted']} !important; font-weight: 600; }}
    [data-testid="stMetricValue"] {{ font-size: 2.2rem !important; font-weight: 700; color: {_tokens['text_primary']} !important; }}
    [data-testid="stMetric"] {{
        background: #ffffff;
        border: 1px solid {_tokens['border']};
        border-radius: 10px;
        padding: 8px 10px;
    }}

    .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; vertical-align: middle; }}
    .badge-approved  {{ background: #1f6b3e; color: #aff5b4; }}
    .badge-changes   {{ background: #7d4e17; color: #ffa657; }}
    .badge-reject    {{ background: #6e2020; color: #ff9a9a; }}
    .badge-completed {{ background: #1a4a7a; color: #a5d6ff; }}

    .stage-row {{ display: flex; align-items: center; justify-content: space-between; padding: 8px 6px; border-radius: 6px; font-size: 0.93rem; color: {_tokens['text_secondary']}; line-height: 1.4; transition: background 0.15s; }}
    .stage-row:hover {{ background: {_tokens['hover']}; }}
    .stage-name {{ flex: 1; }}

    .artifact-tag {{ background: {_tokens['surface_alt']}; border: 1px solid {_tokens['border']}; border-radius: 6px; padding: 4px 12px; font-size: 0.82rem; color: {_tokens['text_muted']}; display: inline-block; margin-bottom: 14px; }}

    .evt {{ padding: 7px 0; border-bottom: 1px solid {_tokens['border']}; font-size: 0.88rem; color: {_tokens['text_secondary']}; line-height: 1.5; }}
    .evt:last-child {{ border-bottom: none; }}
    .evt-time {{ color: {_tokens['text_muted']}; font-size: 0.78rem; }}

    .wf-legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 16px; }}
    .wf-chip {{ border: 1px solid {_tokens['border']}; border-radius: 999px; padding: 4px 10px; font-size: 0.78rem; color: {_tokens['text_secondary']}; background: {_tokens['chip_bg']}; }}
    .wf-chip.approved {{ border-color: #16a34a; color: #16a34a; }}
    .wf-chip.changes {{ border-color: #ea580c; color: #ea580c; }}
    .wf-chip.current {{ border-color: #2563eb; color: #2563eb; }}
    .wf-chip.completed {{ border-color: {_tokens['border']}; color: {_tokens['text_secondary']}; }}

    .wf-node {{ border: 1px solid {_tokens['border']}; border-radius: 10px; padding: 12px 14px; background: {_tokens['surface']}; margin: 6px 0; }}
    .wf-node.completed {{ border-left: 4px solid #94a3b8; }}
    .wf-node.current {{ border-left: 4px solid #2563eb; background: {_tokens['wf_current_bg']}; }}
    .wf-node.loop {{ border: 1px solid #f59e0b; background: {_tokens['wf_loop_bg']}; }}

    .wf-node-top {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 6px; }}
    .wf-stage {{ font-weight: 700; color: {_tokens['text_primary']}; font-size: 0.95rem; }}
    .wf-meta {{ color: {_tokens['text_muted']}; font-size: 0.8rem; }}
    .wf-arrow {{ text-align: center; color: {_tokens['text_muted']}; font-size: 0.92rem; margin: 2px 0 2px; }}
    .wf-arrow.loop {{ color: #c2410c; font-weight: 700; }}

    hr {{ border-color: {_tokens['border']} !important; }}
    [data-testid="stExpander"] summary {{ font-size: 1rem !important; font-weight: 500; }}
    [data-testid="stExpander"] {{
        background: #ffffff;
        border: 1px solid {_tokens['border']};
        border-radius: 10px;
    }}
    [data-testid="stExpander"] details {{
        background: #ffffff;
        border-radius: 10px;
    }}

    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        background: #ffffff !important;
        border-color: {_tokens['border']} !important;
    }}

    [data-testid="stTabs"] [role="tabpanel"] {{
        background: #ffffff;
        border: 1px solid {_tokens['border']};
        border-radius: 10px;
        padding: 12px 14px;
    }}
    [data-testid="stSidebar"] [data-testid="stSelectbox"] label {{ font-size: 0.9rem !important; font-weight: 600; color: {_tokens['text_secondary']} !important; }}
    [data-testid="stTabs"] button {{ font-size: 0.95rem !important; font-weight: 600 !important; }}
    h1 {{ font-size: 1.85rem !important; }}
    h3 {{ font-size: 1.2rem !important; }}
    footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=5)
def load_readme() -> dict[str, str]:
    path = DEMO_OUTPUT / "README.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data: dict[str, str] = {}
    for line in text.splitlines():
        # Format: "- key: value"  or  "**key**: value"
        m = re.match(r"[-*]\s+([\w_]+):\s+(.+)", line) or re.match(r"\*\*(.+?)\*\*[:\s]+(.+)", line)
        if m:
            data[m.group(1).strip()] = m.group(2).strip()
    return data


@st.cache_data(ttl=5)
def load_artifacts() -> list[dict[str, Any]]:
    """Return list of artifact dicts, each with parsed JSON metadata + md_content."""
    arts_dir = DEMO_OUTPUT / "artifacts"
    if not arts_dir.exists():
        return []

    # Build uuid → md file mapping
    md_by_uuid: dict[str, Path] = {}
    for f in arts_dir.glob("*.md"):
        uuid = f.stem.split("_")[0]
        md_by_uuid[uuid] = f

    artifacts = []
    for json_file in sorted(arts_dir.glob("*.json")):
        uuid = json_file.stem.split("_")[0]
        artifact_type = "_".join(json_file.stem.split("_")[1:])
        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        md_content = ""
        if uuid in md_by_uuid:
            try:
                md_content = md_by_uuid[uuid].read_text(encoding="utf-8")
            except Exception:
                pass

        artifacts.append({
            "uuid": uuid,
            "type": artifact_type,
            "stage": meta.get("stage", "UNKNOWN"),
            "version": meta.get("version", 1),
            "created_by": meta.get("created_by", ""),
            "status": meta.get("status", ""),
            "meta": meta,
            "md": md_content,
        })

    def artifact_sort_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
        stage = str(item.get("stage", "UNKNOWN"))
        try:
            stage_index = STAGE_ORDER.index(stage)
        except ValueError:
            stage_index = len(STAGE_ORDER)

        version = int(item.get("version", 1) or 1)
        created_at = str(item.get("meta", {}).get("created_at", ""))
        uuid = str(item.get("uuid", ""))
        return stage_index, version, created_at, uuid

    artifacts.sort(key=artifact_sort_key)
    return artifacts


@st.cache_data(ttl=5)
def load_events() -> list[dict[str, Any]]:
    path = DEMO_OUTPUT / "events.jsonl"
    if not path.exists():
        return []
    events = []
    seen_event_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                event = json.loads(line)
                event_id = str(event.get("event_id", ""))
                if event_id:
                    if event_id in seen_event_ids:
                        continue
                    seen_event_ids.add(event_id)
                events.append(event)
            except Exception:
                pass
    events.sort(key=lambda item: (str(item.get("timestamp", "")), str(item.get("event_id", ""))))
    return events


@st.cache_data(ttl=5)
def load_snapshots() -> dict[str, list[dict]]:
    """Return {stage_key: [snapshot, ...]} ordered by step number."""
    snaps_dir = DEMO_OUTPUT / "state_snapshots"
    if not snaps_dir.exists():
        return {}
    by_stage: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(snaps_dir.glob("step_*.json")):
        try:
            snap = json.loads(f.read_text(encoding="utf-8"))
            stage = snap.get("current_stage", "UNKNOWN")
            snap["_filename"] = f.name
            by_stage[stage].append(snap)
        except Exception:
            pass
    return dict(by_stage)


# ── Helpers ──────────────────────────────────────────────────────────────────


def decision_badge(decision: str) -> str:
    cls = {
        "APPROVED": "badge-approved",
        "REQUEST_CHANGES": "badge-changes",
        "REJECT": "badge-reject",
    }.get(decision, "badge-completed")
    label = decision.replace("_", " ")
    return f'<span class="badge {cls}">{label}</span>'


def stage_decisions(events: list[dict]) -> dict[str, list[str]]:
    """Map stage → list of decision strings from events."""
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
    matches: list[dict] = []
    for artifact in artifacts:
        if artifact.get("type") != artifact_type:
            continue
        if stage is not None and artifact.get("stage") != stage:
            continue
        matches.append(artifact)

    if not matches:
        return None

    def sort_key(artifact: dict) -> tuple[int, str, str]:
        version = int(artifact.get("version", 1) or 1)
        created_at = str(artifact.get("meta", {}).get("created_at", ""))
        artifact_id = str(artifact.get("meta", {}).get("artifact_id", artifact.get("uuid", "")))
        return version, created_at, artifact_id

    return max(matches, key=sort_key)


def first_artifact(
    artifacts: list[dict],
    stage: str,
    version: int,
    artifact_type: str,
) -> dict | None:
    for artifact in artifacts:
        if (
            artifact.get("stage") == stage
            and int(artifact.get("version", 1)) == version
            and artifact.get("type") == artifact_type
        ):
            return artifact
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
    repo_profile = "unknown"
    sandbox_path = "N/A"

    if latest_scan:
        payload = latest_scan.get("payload", {})
        seed_repo_name = str(payload.get("seed_repo_name", "unknown"))
        sandbox_path = str(payload.get("sandbox_path", "N/A"))

    latest_impl = latest_artifact(artifacts, "CodeImplementation", "IMPLEMENTATION")
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
    for role in role_order:
        role_stages = [
            stage for stage in STAGE_ORDER
            if STAGE_META.get(stage, ("", "", ""))[2] == role
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
            if revision_span <= 1:
                status = "Completed"
            else:
                status = f"Worked across {revision_span} revisions"

        rows.append(
            {
                "role": role,
                "status": status,
                "cycles": revision_span,
                "last_stage": last_stage,
            }
        )
    return rows


def run_workflow_from_dashboard(
    seed_repo_name: str,
    repo_url: str | None = None,
    repo_ref: str | None = None,
) -> tuple[bool, str]:
    try:
        env = {
            **os.environ,
            "PYTHONPATH": "src",
            "ASF_SEED_REPO": seed_repo_name,
            "ASF_PERSISTENCE_BACKEND": "sqlite",
            "ASF_SQLITE_PATH": UI_SQLITE_PATH,
        }
        if repo_url:
            env["ASF_REPO_URL"] = repo_url
        if repo_ref:
            env["ASF_REPO_REF"] = repo_ref

        result = subprocess.run(
            [sys.executable, "-m", "ai_software_factory"],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to run workflow: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Workflow failed with no output."
    return True, output[-4000:] if output else "Workflow completed successfully."


def run_escalation_demo_from_dashboard() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/demo_escalation.py"],
            cwd=BASE_DIR,
            env={
                **os.environ,
                "PYTHONPATH": "src",
                "ASF_PERSISTENCE_BACKEND": "sqlite",
                "ASF_SQLITE_PATH": UI_SQLITE_PATH,
            },
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to run escalation demo: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Escalation demo failed with no output."
    return True, output[-4000:] if output else "Escalation demo completed successfully."


def run_resume_from_dashboard(workflow_id: str, human_response: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ai_software_factory"],
            cwd=BASE_DIR,
            env={
                **os.environ,
                "PYTHONPATH": "src",
                "ASF_PERSISTENCE_BACKEND": "sqlite",
                "ASF_SQLITE_PATH": UI_SQLITE_PATH,
                "ASF_RESUME_WORKFLOW_ID": workflow_id,
                "ASF_HUMAN_RESPONSE": human_response,
            },
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Failed to resume workflow: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        return False, output[-4000:] if output else "Workflow resume failed with no output."
    return True, output[-4000:] if output else "Workflow resumed successfully."


def latest_escalation_reason(events: list[dict]) -> str | None:
    for event in reversed(events):
        if event.get("event_type") != "ESCALATION_RAISED":
            continue
        payload = event.get("payload", {})
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None


def planner_insights_by_revision(events: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("event_type") != "CHANGE_PLAN_GENERATED":
            continue
        payload = event.get("payload", {})
        revision = payload.get("revision")
        if not isinstance(revision, int):
            continue
        grouped[revision].append(
            {
                "summary": payload.get("summary", ""),
                "confidence": payload.get("confidence", "UNKNOWN"),
                "files_to_modify": payload.get("files_to_modify", []),
                "target_symbols": payload.get("target_symbols", {}),
                "target_confidence": payload.get("target_confidence", {}),
                "intent_category": payload.get("intent_category", "GENERAL"),
            }
        )
    return dict(grouped)


def patch_events_by_revision(events: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        event_type = event.get("event_type")
        if event_type not in {"PATCH_APPLIED", "PATCH_ROLLED_BACK"}:
            continue
        payload = event.get("payload", {})
        revision = payload.get("revision")
        if not isinstance(revision, int):
            continue
        grouped[revision].append(
            {
                "event_type": event_type,
                "file_path": payload.get("file_path", "unknown"),
                "operation": payload.get("operation", "unknown"),
                "symbols": payload.get("symbols", []),
                "message": payload.get("message", ""),
            }
        )
    return dict(grouped)


def build_graph_nodes(events: list[dict]) -> list[dict]:
    transitions = [
        e for e in events
        if e.get("event_type") == "TRANSITION_OCCURRED"
        and e.get("payload", {}).get("from_stage")
        and e.get("payload", {}).get("to_stage")
    ]
    if not transitions:
        return []

    first_transition = transitions[0]
    start_stage = first_transition.get("payload", {}).get("from_stage", "BACKLOG_INTAKE")

    nodes: list[dict] = [{
        "stage": start_stage,
        "revision": 1,
        "loop_entry": False,
    }]

    prev_revision = 1
    for transition in transitions:
        payload = transition.get("payload", {})
        to_stage = payload.get("to_stage", "")
        next_revision = payload.get("revision", prev_revision)
        if not isinstance(next_revision, int):
            next_revision = prev_revision

        loop_entry = to_stage == "IMPLEMENTATION" and next_revision > prev_revision
        nodes.append(
            {
                "stage": to_stage,
                "revision": next_revision,
                "loop_entry": loop_entry,
            }
        )
        prev_revision = next_revision

    return nodes


def render_workflow_graph_tab(readme: dict, events: list[dict], snapshots: dict) -> None:
    st.markdown("### 🧭 Workflow Graph")
    st.markdown(
        "Visual path of the current run, including review decisions and revision loops."
    )

    nodes = build_graph_nodes(events)
    if not nodes:
        st.info("No transition data found yet. Run the workflow to generate graph data.")
        return

    decision_map = stage_decisions(events)
    stage_counts = defaultdict(int)
    for node in nodes:
        stage_counts[node["stage"]] += 1

    latest = latest_snapshot(snapshots)
    current_stage = latest.get("current_stage") or readme.get("final_stage", "DONE")
    current_revision = latest.get("revision")
    if not isinstance(current_revision, int):
        try:
            current_revision = int(readme.get("revision_count", "1"))
        except ValueError:
            current_revision = 1

    loop_count = sum(1 for node in nodes if node.get("loop_entry"))
    if loop_count > 0:
        st.warning(f"Revision loop detected: {loop_count} loop event(s) in this run.", icon="🔄")
    else:
        st.success("Happy path detected: no revision loops in this run.", icon="✅")

    st.markdown(
        """
        <div class="wf-legend">
            <span class="wf-chip approved">APPROVED</span>
            <span class="wf-chip changes">REQUEST_CHANGES</span>
            <span class="wf-chip current">CURRENT_STAGE</span>
            <span class="wf-chip completed">COMPLETED_STAGE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    decision_index: dict[str, int] = defaultdict(int)

    for index, node in enumerate(nodes):
        stage = node["stage"]
        revision = node["revision"]
        icon, _, _ = STAGE_META.get(stage, ("•", stage, ""))

        show_revision = stage_counts[stage] > 1 or stage in {
            "IMPLEMENTATION",
            "PULL_REQUEST_CREATED",
            "ARCHITECTURE_REVIEW_GATE",
            "PEER_CODE_REVIEW_GATE",
            "TEST_VALIDATION_GATE",
            "PRODUCT_ACCEPTANCE_GATE",
        }
        title = f"{stage} (Rev {revision})" if show_revision else stage

        decision = ""
        if stage in REVIEW_GATES:
            decision_list = decision_map.get(stage, [])
            current_decision_index = decision_index[stage]
            if current_decision_index < len(decision_list):
                decision = decision_list[current_decision_index]
            decision_index[stage] += 1

        node_status_class = "completed"
        status_label = "COMPLETED_STAGE"
        is_last = index == len(nodes) - 1
        if is_last and stage == current_stage:
            if stage != "DONE":
                node_status_class = "current"
                status_label = "CURRENT_STAGE"
            else:
                node_status_class = "completed"
                status_label = "COMPLETED_STAGE"

        if node.get("loop_entry"):
            node_status_class = f"{node_status_class} loop"

        decision_badge_html = ""
        if decision == "APPROVED":
            decision_badge_html = '<span class="wf-chip approved">APPROVED</span>'
        elif decision == "REQUEST_CHANGES":
            decision_badge_html = '<span class="wf-chip changes">REQUEST_CHANGES</span>'

        status_badge_html = (
            '<span class="wf-chip current">CURRENT_STAGE</span>'
            if status_label == "CURRENT_STAGE"
            else '<span class="wf-chip completed">COMPLETED_STAGE</span>'
        )

        st.markdown(
            f"""
            <div class="wf-node {node_status_class}">
                <div class="wf-node-top">
                    <div class="wf-stage">{icon} {title}</div>
                    <div>{decision_badge_html} {status_badge_html}</div>
                </div>
                <div class="wf-meta">Revision {revision}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if index < len(nodes) - 1:
            next_node = nodes[index + 1]
            if next_node.get("loop_entry"):
                st.markdown('<div class="wf-arrow loop">⬇ Revision loop back to IMPLEMENTATION</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="wf-arrow">⬇</div>', unsafe_allow_html=True)


def render_execution_tab(readme: dict, artifacts: list[dict], events: list[dict]) -> None:
    st.markdown("### ⚙️ Real Execution")
    st.markdown("Generated code, tests, and real pytest execution for the current workflow run.")

    active_context = detect_active_context(artifacts, events)

    latest_impl = latest_artifact(artifacts, "CodeImplementation", "IMPLEMENTATION")
    latest_test = latest_artifact(artifacts, "TestResult", "TEST_VALIDATION_GATE")

    workspace_path = (
        (latest_impl.get("meta", {}).get("workspace_path") if latest_impl else "")
        or readme.get("generated_workspace_path", "N/A")
    )
    source_files = (latest_impl.get("meta", {}).get("written_source_files", []) if latest_impl else [])
    test_files = (latest_test.get("meta", {}).get("generated_test_files", []) if latest_test else [])

    status = "UNKNOWN"
    if latest_test:
        status = "PASSED" if latest_test.get("meta", {}).get("passed", False) else "FAILED"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workspace", "Ready" if workspace_path and workspace_path != "N/A" else "Missing")
    c2.metric("Source Files", len(source_files))
    c3.metric("Test Files", len(test_files))
    c4.metric("pytest Result", status)

    st.markdown(
        f"""
        <div style="background:{_tokens['surface']};border:1px solid {_tokens['border']};border-radius:10px;padding:14px 16px;margin:12px 0 18px">
            <div style="color:{_tokens['text_muted']};font-size:0.78rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Active Scenario</div>
            <div style="font-size:1.05rem;font-weight:700;color:{_tokens['text_primary']};margin-bottom:6px">{active_context['scenario_title']}</div>
            <div style="display:flex;gap:20px;flex-wrap:wrap;color:{_tokens['text_secondary']};font-size:0.88rem">
                <span>🧪 Repo source: <strong>{active_context['seed_repo_name']}</strong></span>
                <span>🧭 Repo profile: <strong>{active_context['repo_profile']}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"**Generated workspace path:** {workspace_path}")

    lane_summaries: list[str] = []
    for event in reversed(events):
        if event.get("event_type") != "FILES_MODIFIED":
            continue
        payload = event.get("payload", {})
        lane_values = payload.get("engineer_lanes", [])
        if isinstance(lane_values, list):
            lane_summaries = [str(item) for item in lane_values]
        break

    if lane_summaries:
        st.markdown("**Parallel engineer lanes**")
        for lane in lane_summaries:
            st.markdown(f"- {lane}")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Generated Source Files")
        if source_files:
            for path in source_files:
                st.markdown(f"- {path}")
        else:
            st.info("No source files recorded yet.")

    with right:
        st.markdown("#### Generated Test Files")
        if test_files:
            for path in test_files:
                st.markdown(f"- {path}")
        else:
            st.info("No test files recorded yet.")

    if not latest_test:
        st.info("No pytest execution artifact found yet.")
        return

    test_meta = latest_test.get("meta", {})
    st.divider()
    st.markdown("#### pytest Execution Summary")
    st.markdown(f"**Command:** `{test_meta.get('test_command', 'N/A')}`")
    st.markdown(f"**Run log:** {test_meta.get('run_log_path', 'N/A')}")
    st.markdown(f"**Failed tests:** {test_meta.get('failed_cases', 0)}")

    failing_tests = test_meta.get("failing_tests", [])
    if failing_tests:
        st.markdown("**Failing test names**")
        for test_name in failing_tests:
            st.markdown(f"- {test_name}")

    with st.expander("pytest stdout", expanded=False):
        stdout = test_meta.get("stdout", "")
        if stdout:
            st.code(stdout[-8000:], language="text")
        else:
            st.caption("No stdout captured.")

    with st.expander("pytest stderr", expanded=False):
        stderr = test_meta.get("stderr", "")
        if stderr:
            st.code(stderr[-8000:], language="text")
        else:
            st.caption("No stderr captured.")

    st.divider()
    st.markdown("#### Planning Intent (What the Agent Planned)")
    grouped_plans = planner_insights_by_revision(events)
    if not grouped_plans:
        st.info("No planner insights recorded for this run.")
    else:
        for revision in sorted(grouped_plans.keys()):
            for plan in grouped_plans[revision]:
                with st.expander(f"Revision {revision} · Planner Confidence: {plan['confidence']}", expanded=False):
                    if plan["summary"]:
                        st.markdown(plan["summary"])
                    st.markdown(f"**Intent category:** {plan['intent_category']}")
                    st.markdown("**Files to modify**")
                    for file_name in plan["files_to_modify"]:
                        st.markdown(f"- {file_name}")
                    st.markdown("**Target symbols**")
                    if plan["target_symbols"]:
                        for file_name, symbols in plan["target_symbols"].items():
                            pretty_symbols = ", ".join(symbols) if symbols else "(none)"
                            st.markdown(f"- {file_name}: {pretty_symbols}")
                    else:
                        st.markdown("- No symbol-level targets recorded")
                    st.markdown("**Target confidence**")
                    if plan["target_confidence"]:
                        for file_name, score in plan["target_confidence"].items():
                            st.markdown(f"- {file_name}: {float(score):.2f}")
                    else:
                        st.markdown("- No confidence scores recorded")


# ── Summary helpers ────────────────────────────────────────────────────────────


def build_stage_timeline(
    artifacts: list[dict],
    events: list[dict],
    snapshots: dict,
) -> list[dict]:
    """
    Return one row per executed stage (revision-aware) with:
      stage, label, icon, role, artifact_types, decision, is_gate, revision
    """
    decisions_map = stage_decisions(events)
    by_stage = artifacts_by_stage(artifacts)
    rows = []

    for s in STAGE_ORDER:
        snaps = snapshots.get(s, [])
        icon, label, role = STAGE_META.get(s, ("•", s, ""))

        if s == "DONE":
            rows.append({
                "stage": s, "label": label, "icon": icon, "role": role,
                "artifact_types": [], "decision": "COMPLETED", "is_gate": False,
                "revision": None,
            })
            continue

        if not snaps:
            continue

        dec_list = decisions_map.get(s, [])
        multi = len(snaps) > 1

        for i, snap in enumerate(snaps):
            rev = snap.get("revision", i + 1)
            stage_arts = [
                a for a in by_stage.get(s, [])
                if not multi or a["version"] == rev
            ]
            art_types = list(dict.fromkeys(
                ARTIFACT_TYPE_LABELS.get(a["type"], a["type"]) for a in stage_arts
            ))
            dec = dec_list[i] if i < len(dec_list) else ""
            rows.append({
                "stage": s,
                "label": f"{label} (Rev {rev})" if multi else label,
                "icon": icon,
                "role": role,
                "artifact_types": art_types,
                "decision": dec,
                "is_gate": s in REVIEW_GATES,
                "revision": rev,
            })
    return rows


def extract_key_decisions(artifacts: list[dict], events: list[dict]) -> list[dict]:
    """
    For each review gate that was APPROVED, pull the ReviewFeedback meta
    and return a structured summary entry.
    """
    decisions_map = stage_decisions(events)
    by_stage = artifacts_by_stage(artifacts)
    result = []

    gate_labels = {
        "ARCHITECTURE_REVIEW_GATE": "Architecture Review",
        "PEER_CODE_REVIEW_GATE":    "Peer Code Review",
        "TEST_VALIDATION_GATE":     "Test Validation",
        "PRODUCT_ACCEPTANCE_GATE":  "Product Acceptance",
    }

    for gate, gate_label in gate_labels.items():
        dec_list = decisions_map.get(gate, [])
        arts = [a for a in by_stage.get(gate, []) if a["type"] == "ReviewFeedback"]

        for i, dec in enumerate(dec_list):
            if dec != "APPROVED":
                continue
            art = arts[i] if i < len(arts) else (arts[-1] if arts else None)
            if not art:
                continue
            meta = art["meta"]
            result.append({
                "gate": gate_label,
                "reviewer": meta.get("reviewer", meta.get("created_by", "")),
                "summary": meta.get("comments", meta.get("summary", "")),
                "notes": meta.get("notes", ""),
                "revision": art["version"],
            })
    gate_order_index = {
        "Architecture Review": 0,
        "Peer Code Review": 1,
        "Test Validation": 2,
        "Product Acceptance": 3,
    }
    result.sort(key=lambda item: (gate_order_index.get(str(item.get("gate", "")), 999), int(item.get("revision", 0) or 0)))
    return result


def extract_key_issues(artifacts: list[dict], events: list[dict]) -> list[dict]:
    """
    Find REQUEST_CHANGES decisions and pull issues + suggested_changes
    from the associated ReviewFeedback / TestResult artifacts.
    """
    result = []
    by_stage = artifacts_by_stage(artifacts)

    gate_sequence = [
        "ARCHITECTURE_REVIEW_GATE",
        "PEER_CODE_REVIEW_GATE",
        "TEST_VALIDATION_GATE",
        "PRODUCT_ACCEPTANCE_GATE",
    ]

    for stage in gate_sequence:
        _, label, _ = STAGE_META.get(stage, ("•", stage, ""))
        review_feedback = [
            art
            for art in by_stage.get(stage, [])
            if art.get("type") == "ReviewFeedback"
        ]

        review_feedback.sort(
            key=lambda art: (
                int(art.get("version", 1) or 1),
                str(art.get("meta", {}).get("created_at", "")),
                str(art.get("uuid", "")),
            )
        )

        for feedback in review_feedback:
            meta = feedback.get("meta", {})
            if meta.get("decision") != "REQUEST_CHANGES":
                continue

            revision = int(feedback.get("version", 1) or 1)
            issues = list(meta.get("issues_identified", []))
            suggestions = list(meta.get("suggested_changes", []))
            artifact_type_label = ARTIFACT_TYPE_LABELS.get("ReviewFeedback", "ReviewFeedback")

            matching_test = next(
                (
                    art
                    for art in by_stage.get(stage, [])
                    if art.get("type") == "TestResult"
                    and int(art.get("version", 1) or 1) == revision
                ),
                None,
            )
            if matching_test:
                test_meta = matching_test.get("meta", {})
                failing = test_meta.get("failing_tests", [])
                if failing:
                    issues = [f"Failing test: {name}" for name in failing]
                    artifact_type_label = ARTIFACT_TYPE_LABELS.get("TestResult", "TestResult")
                test_suggestions = test_meta.get("suggested_changes", [])
                if test_suggestions:
                    suggestions = list(test_suggestions)

            if issues or suggestions:
                result.append(
                    {
                        "stage_label": label,
                        "gate": stage,
                        "artifact_type": artifact_type_label,
                        "issues": issues,
                        "suggestions": suggestions,
                        "revision": revision,
                    }
                )
    result.sort(
        key=lambda item: (
            STAGE_ORDER.index(item["gate"]) if item["gate"] in STAGE_ORDER else 999,
            int(item.get("revision", 0) or 0),
        )
    )
    return result


def detect_revision_cycles(events: list[dict]) -> list[dict]:
    """Detect revision loops from REQUEST_CHANGES + REVISION_STARTED events."""
    cycles = []
    for index, event in enumerate(events):
        if event.get("event_type") != "REVISION_STARTED":
            continue

        stage = event.get("stage", "")
        payload = event.get("payload", {})
        next_revision = payload.get("new_revision")
        if not isinstance(next_revision, int) or next_revision <= 1:
            continue

        failed_revision = next_revision - 1
        decision_notes = ""
        for prior in reversed(events[:index]):
            if (
                prior.get("event_type") == "DECISION_MADE"
                and prior.get("stage") == stage
                and prior.get("payload", {}).get("decision") == "REQUEST_CHANGES"
            ):
                decision_notes = prior.get("payload", {}).get("notes", "")
                break

        cycles.append(
            {
                "gate": stage,
                "failed_revision": failed_revision,
                "next_revision": next_revision,
                "decision": "REQUEST_CHANGES",
                "decision_notes": decision_notes,
            }
        )
    return cycles


def infer_cycle_reason(cycle: dict, artifacts: list[dict]) -> dict:
    gate = cycle["gate"]
    failed_revision = cycle["failed_revision"]

    feedback = first_artifact(artifacts, gate, failed_revision, "ReviewFeedback")
    test_result = first_artifact(artifacts, gate, failed_revision, "TestResult")

    summary = ""
    issues: list[str] = []

    if feedback:
        feedback_meta = feedback.get("meta", {})
        summary = feedback_meta.get("comments") or feedback_meta.get("summary") or summary
        issues.extend(feedback_meta.get("issues_identified", []))

    if test_result:
        test_meta = test_result.get("meta", {})
        failing_tests = test_meta.get("failing_tests", [])
        if failing_tests:
            issues.extend([f"Failing test: {name}" for name in failing_tests])
        details = test_meta.get("details", [])
        if details and len(issues) < 6:
            issues.extend(details[: max(0, 6 - len(issues))])

    if not summary:
        summary = cycle.get("decision_notes") or "Gate requested changes due to validation or review findings."

    return {
        "summary": summary,
        "issues": issues,
    }


def infer_next_revision_changes(cycle: dict, artifacts: list[dict]) -> dict:
    failed_revision = cycle["failed_revision"]
    next_revision = cycle["next_revision"]

    implementation_prev = first_artifact(artifacts, "IMPLEMENTATION", failed_revision, "CodeImplementation")
    implementation_next = first_artifact(artifacts, "IMPLEMENTATION", next_revision, "CodeImplementation")

    pull_request_prev = first_artifact(artifacts, "PULL_REQUEST_CREATED", failed_revision, "PullRequest")
    pull_request_next = first_artifact(artifacts, "PULL_REQUEST_CREATED", next_revision, "PullRequest")

    tests_prev = first_artifact(artifacts, "TEST_VALIDATION_GATE", failed_revision, "TestResult")
    tests_next = first_artifact(artifacts, "TEST_VALIDATION_GATE", next_revision, "TestResult")

    architecture_review_prev = first_artifact(artifacts, "ARCHITECTURE_REVIEW_GATE", failed_revision, "ReviewFeedback")
    architecture_review_next = first_artifact(artifacts, "ARCHITECTURE_REVIEW_GATE", next_revision, "ReviewFeedback")

    implementation_changes: list[str] = []
    if implementation_prev and implementation_next:
        previous_files = implementation_prev.get("meta", {}).get("files_changed", [])
        next_files = implementation_next.get("meta", {}).get("files_changed", [])
        added_files = list_added(previous_files, next_files)
        if added_files:
            implementation_changes.extend([f"Added/updated: {item}" for item in added_files[:6]])
        previous_summary = implementation_prev.get("meta", {}).get("summary", "")
        next_summary = implementation_next.get("meta", {}).get("summary", "")
        if next_summary and next_summary != previous_summary:
            implementation_changes.append(next_summary)
    elif implementation_next:
        implementation_changes.append(
            implementation_next.get("meta", {}).get("summary", "Implementation updated in next revision.")
        )

    additional_tests: list[str] = []
    if tests_prev and tests_next:
        prev_meta = tests_prev.get("meta", {})
        next_meta = tests_next.get("meta", {})
        prev_tests = prev_meta.get("unit_tests", []) + prev_meta.get("integration_tests", [])
        next_tests = next_meta.get("unit_tests", []) + next_meta.get("integration_tests", [])
        new_tests = list_added(prev_tests, next_tests)
        if new_tests:
            additional_tests.extend([f"Added test: {test_name}" for test_name in new_tests[:6]])

        prev_failed = int(prev_meta.get("failed_cases", 0))
        next_failed = int(next_meta.get("failed_cases", 0))
        if next_failed < prev_failed:
            additional_tests.append(f"Failed tests reduced from {prev_failed} to {next_failed}.")
        coverage_estimate = next_meta.get("coverage_estimate")
        if coverage_estimate:
            additional_tests.append(f"Validation result: {coverage_estimate}")

    architecture_adjustments: list[str] = []
    if pull_request_prev and pull_request_next:
        prev_pr_files = pull_request_prev.get("meta", {}).get("files_modified", [])
        next_pr_files = pull_request_next.get("meta", {}).get("files_modified", [])
        pr_deltas = list_added(prev_pr_files, next_pr_files)
        if pr_deltas:
            architecture_adjustments.extend([f"Pull request scope expanded: {item}" for item in pr_deltas[:5]])

    if architecture_review_prev and architecture_review_next:
        prev_notes = architecture_review_prev.get("meta", {}).get("comments", "")
        next_notes = architecture_review_next.get("meta", {}).get("comments", "")
        if next_notes and next_notes != prev_notes:
            architecture_adjustments.append("Architecture review notes were updated and re-approved.")

    return {
        "implementation_changes": implementation_changes,
        "additional_tests": additional_tests,
        "architecture_adjustments": architecture_adjustments,
    }


def artifact_highlights(artifact: dict[str, Any]) -> list[str]:
    meta = artifact.get("meta", {})
    lines: list[str] = []

    decision = meta.get("decision")
    if isinstance(decision, str) and decision:
        lines.append(f"Decision: {decision}")

    for key in ("title", "summary", "comments"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(value.strip())
            break

    if artifact.get("type") == "TestResult":
        passed = meta.get("passed")
        failed_cases = meta.get("failed_cases")
        total_cases = meta.get("total_cases")
        if isinstance(passed, bool):
            status = "PASSED" if passed else "FAILED"
            lines.append(f"pytest status: {status}")
        if isinstance(failed_cases, int) and isinstance(total_cases, int):
            lines.append(f"Test cases: {total_cases} total, {failed_cases} failing")
        failing_tests = meta.get("failing_tests", [])
        if isinstance(failing_tests, list) and failing_tests:
            lines.append(f"Failing tests: {', '.join(str(item) for item in failing_tests[:3])}")

    files_changed = meta.get("files_changed", [])
    if isinstance(files_changed, list) and files_changed:
        lines.append(f"Files changed: {', '.join(str(item) for item in files_changed[:3])}")

    suggested_changes = meta.get("suggested_changes", [])
    if isinstance(suggested_changes, list) and suggested_changes:
        is_acceptance_approved = (
            str(artifact.get("stage", "")) == "PRODUCT_ACCEPTANCE_GATE"
            and str(meta.get("decision", "")) == "APPROVED"
        )
        label = "Acceptance checklist" if is_acceptance_approved else "Suggested changes"
        lines.append(f"{label}: {str(suggested_changes[0])}")

    created_at = meta.get("created_at")
    if isinstance(created_at, str) and created_at:
        lines.append(f"Created at: {created_at}")

    return lines[:5]


def render_revision_insights_tab(artifacts: list[dict], events: list[dict]) -> None:
    st.markdown("### 🔄 Revision Insights")
    st.markdown(
        "This view explains where revision loops happened, why they were triggered, and what improved in the next revision."
    )

    cycles = detect_revision_cycles(events)
    plan_by_revision = planner_insights_by_revision(events)
    patches_by_revision = patch_events_by_revision(events)
    if not cycles:
        st.success("No revision loops detected in this run.", icon="✅")
        return

    for cycle in cycles:
        gate = cycle["gate"]
        _, gate_label, _ = STAGE_META.get(gate, ("•", gate, ""))
        failed_revision = cycle["failed_revision"]
        next_revision = cycle["next_revision"]

        tests_prev = first_artifact(artifacts, "TEST_VALIDATION_GATE", failed_revision, "TestResult")
        tests_next = first_artifact(artifacts, "TEST_VALIDATION_GATE", next_revision, "TestResult")
        auto_expand = False
        if tests_prev and tests_next:
            prev_failing = tests_prev.get("meta", {}).get("failing_tests", [])
            next_failing = tests_next.get("meta", {}).get("failing_tests", [])
            unresolved = [item for item in prev_failing if item in next_failing]
            auto_expand = len(unresolved) > 0

        reason = infer_cycle_reason(cycle, artifacts)
        changes = infer_next_revision_changes(cycle, artifacts)

        with st.expander(
            f"Revision {failed_revision} Failed → Revision {next_revision}",
            expanded=auto_expand,
        ):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**Revision {failed_revision} Failed**")
            col_b.markdown(f"**Gate:** `{gate}`")
            col_c.markdown(f"**Decision:** `{cycle['decision']}`")

            st.markdown(f"<small style='color:#8b949e'>{gate_label}</small>", unsafe_allow_html=True)
            st.divider()

            st.markdown("#### Reason")
            st.markdown(reason["summary"])
            if reason["issues"]:
                st.markdown("**Review feedback / validation issues**")
                for issue in reason["issues"]:
                    st.markdown(f"- {issue}")

            st.divider()
            st.markdown(f"#### Changes in Next Revision (Revision {next_revision})")

            st.markdown("**Implementation changes**")
            if changes["implementation_changes"]:
                for item in changes["implementation_changes"]:
                    st.markdown(f"- {item}")
            else:
                st.markdown("- No explicit implementation delta recorded; revision artifacts indicate refinements.")

            st.markdown("**Additional tests added**")
            if changes["additional_tests"]:
                for item in changes["additional_tests"]:
                    st.markdown(f"- {item}")
            else:
                st.markdown("- No new test names detected; existing tests were re-run with improved outcomes.")

            st.markdown("**Architecture adjustments**")
            if changes["architecture_adjustments"]:
                for item in changes["architecture_adjustments"]:
                    st.markdown(f"- {item}")
            else:
                st.markdown("- No major architecture change detected; loop focused on implementation and validation fixes.")

            st.divider()
            st.markdown("#### Planner Decisions for This Revision")
            plans_for_next = plan_by_revision.get(next_revision, [])
            if not plans_for_next:
                st.markdown("- No planner payload found for this revision.")
            else:
                for plan in plans_for_next:
                    st.markdown(f"- Confidence: **{plan['confidence']}**")
                    st.markdown(f"- Intent category: **{plan['intent_category']}**")
                    if plan["summary"]:
                        st.markdown(f"- Plan summary: {plan['summary']}")
                    if plan["target_symbols"]:
                        st.markdown("**Target symbols selected**")
                        for file_name, symbols in plan["target_symbols"].items():
                            pretty_symbols = ", ".join(symbols) if symbols else "(none)"
                            st.markdown(f"- {file_name}: {pretty_symbols}")
                    else:
                        st.markdown("- Target symbols: none")

            st.divider()
            st.markdown("#### Applied Changes (What Actually Changed)")
            rev_patches = patches_by_revision.get(next_revision, [])
            if not rev_patches:
                st.markdown("- No patch events found for this revision.")
            else:
                for patch in rev_patches:
                    symbols = ", ".join(patch["symbols"]) if patch["symbols"] else "(none)"
                    status = "APPLIED" if patch["event_type"] == "PATCH_APPLIED" else "ROLLED_BACK"
                    st.markdown(
                        f"- {status}: {patch['file_path']} via {patch['operation']} · symbols: {symbols}"
                    )

            if tests_prev and tests_next:
                prev_failing = tests_prev.get("meta", {}).get("failing_tests", [])
                next_failing = tests_next.get("meta", {}).get("failing_tests", [])
                resolved = [item for item in prev_failing if item not in next_failing]
                if resolved:
                    st.markdown("**Resolved failures**")
                    for failure in resolved:
                        st.markdown(f"- {failure}")
                else:
                    st.markdown("- No failing tests were resolved in this revision.")


def render_summary_tab(
    readme: dict,
    artifacts: list[dict],
    events: list[dict],
    snapshots: dict,
) -> None:
    active_context = detect_active_context(artifacts, events)
    title = get_backlog_title(artifacts)
    problem = get_backlog_problem(artifacts)
    status = effective_workflow_status(readme, events, snapshots)
    wf_id = readme.get("workflow_id", "—")
    revision_count = readme.get("revision_count", "—")
    n_artifacts = len([a for a in artifacts if a["md"]])
    n_events = len(events)
    approved = count_decisions(events, "APPROVED")
    changes_req = count_decisions(events, "REQUEST_CHANGES")
    pull_requests = [a for a in artifacts if a["type"] == "PullRequest"]
    latest_revision = None
    try:
        latest_revision = int(revision_count)
    except (TypeError, ValueError):
        latest_revision = None
    latest_revision_prs = [
        a for a in pull_requests
        if latest_revision is not None and int(a.get("version", 1)) == latest_revision
    ]

    # ── Feature card ──────────────────────────────────────────────────────
    status_badge = (
        '<span class="badge badge-approved">COMPLETED</span>' if status == "COMPLETED"
        else f'<span class="badge badge-changes">{status}</span>'
    )
    st.markdown(
        f"""
        <div style="background:{_tokens['surface']};border:1px solid {_tokens['border']};border-radius:10px;padding:20px 24px;margin-bottom:18px">
            <div style="font-size:1.45rem;font-weight:700;color:{_tokens['text_primary']};margin-bottom:6px">{title}</div>
            <div style="color:{_tokens['text_muted']};font-size:0.9rem;margin-bottom:14px">{problem or 'No problem statement recorded.'}</div>
            <div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:14px;color:{_tokens['text_secondary']};font-size:0.86rem">
                <span>🧪 Repo source: <strong>{active_context['seed_repo_name']}</strong></span>
                <span>🧭 Repo profile: <strong>{active_context['repo_profile']}</strong></span>
                <span>📦 Sandbox: <strong>{active_context['sandbox_path']}</strong></span>
            </div>
            <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">
                <span style="color:{_tokens['text_muted']};font-size:0.82rem">Workflow&nbsp;<code style="color:{_tokens['code_fg']}">{wf_id[:8]}…</code></span>
                <span>{status_badge}</span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">🔄&nbsp;Revisions: <strong>{revision_count}</strong></span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">📎&nbsp;Artifacts: <strong>{n_artifacts}</strong></span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">📡&nbsp;Events: <strong>{n_events}</strong></span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">✅&nbsp;Gates approved: <strong>{approved}</strong></span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">⚠&nbsp;Revision requests: <strong>{changes_req}</strong></span>
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">🔀&nbsp;PRs (latest revision): <strong>{len(latest_revision_prs)}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Team overview ───────────────────────────────────────────────────────
    with st.expander("👥 Autonomous Delivery Team", expanded=False):
        team_rows = team_overview(snapshots)
        cols = st.columns(5)
        for col, row in zip(cols, team_rows):
            col.markdown(f"**{row['role']}**")
            col.markdown(f"<small style='color:#8b949e'>{row['status']}</small>", unsafe_allow_html=True)
            col.caption(f"Last: {row['last_stage']}")

    # ── Parallel engineer lanes visualization ─────────────────────────────
    engineer_lanes = []
    for event in reversed(events):
        if event.get("event_type") != "FILES_MODIFIED":
            continue
        payload = event.get("payload", {})
        lane_values = payload.get("engineer_lanes", [])
        if isinstance(lane_values, list) and lane_values:
            engineer_lanes = lane_values
            break

    if engineer_lanes:
        with st.expander("🔀 Parallel Engineer Lanes", expanded=False):
            st.markdown(f"**{len(engineer_lanes)} engineers working in parallel** on decomposed tasks:")
            cols = st.columns(len(engineer_lanes))
            for col, lane_summary in zip(cols, engineer_lanes):
                lane_parts = lane_summary.split()
                lane_id = lane_parts[0] if lane_parts else "unknown"
                applied = 0
                failed = 0
                for part in lane_parts:
                    if part.startswith("applied="):
                        applied = int(part.split("=")[1])
                    elif part.startswith("failed="):
                        failed = int(part.split("=")[1])

                with col:
                    status_color = "#4ade80" if applied > 0 and failed == 0 else "#f87171" if failed > 0 else "#60a5fa"
                    status_text = f"✅ {applied}" if applied > 0 and failed == 0 else f"❌ {applied}/{failed}" if failed > 0 else "⏳"
                    st.markdown(f"<div style='background:#f0f9ff;border-left:4px solid {status_color};padding:8px;border-radius:6px'><strong>{lane_id}</strong><br><small>{lane_summary.split(lane_id)[1].strip()}</small><div style='margin-top:4px;color:{status_color};font-weight:700'>{status_text}</div></div>", unsafe_allow_html=True)

    with st.expander("Show detailed stage timeline", expanded=False):
        timeline = build_stage_timeline(artifacts, events, snapshots)
        for row in timeline:
            if row.get("stage") == "DONE":
                row["decision"] = status

        # Extract lanes from events for visualization
        lanes_by_revision: dict[int, list[str]] = {}
        for event in reversed(events):
            if event.get("event_type") != "FILES_MODIFIED":
                continue
            payload = event.get("payload", {})
            lane_values = payload.get("engineer_lanes", [])
            revision = payload.get("revision")
            if isinstance(lane_values, list) and lane_values and isinstance(revision, int):
                if revision not in lanes_by_revision:
                    lanes_by_revision[revision] = lane_values

        header_cols = st.columns([3, 2, 4, 2])
        for col, hdr in zip(header_cols, ["Stage", "Agent", "Artifacts Produced", "Decision"]):
            col.markdown(
                f"<small style='color:#8b949e;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.5px'>{hdr}</small>",
                unsafe_allow_html=True,
            )
        st.markdown("<hr style='margin:4px 0 8px;border-color:#30363d'>", unsafe_allow_html=True)

        for row in timeline:
            c1, c2, c3, c4 = st.columns([3, 2, 4, 2])
            c1.markdown(f"{row['icon']} **{row['label']}**")
            c2.markdown(
                f"<span style='color:#8b949e'>{row['role']}</span>",
                unsafe_allow_html=True,
            )
            art_str = ", ".join(row["artifact_types"]) if row["artifact_types"] else "—"
            c3.markdown(
                f"<span style='font-size:0.88rem;color:#c9d1d9'>{art_str}</span>",
                unsafe_allow_html=True,
            )
            if row["decision"]:
                badge = (
                    decision_badge(row["decision"])
                    if row["decision"] != "COMPLETED"
                    else '<span class="badge badge-completed">COMPLETED</span>'
                )
                c4.markdown(badge, unsafe_allow_html=True)

            # Show parallel engineer lanes as sub-rows under IMPLEMENTATION
            if row.get("stage") == "IMPLEMENTATION" and row.get("revision") in lanes_by_revision:
                lanes = lanes_by_revision[row["revision"]]
                st.markdown("<div style='margin-left:20px;margin-top:4px;margin-bottom:8px;padding-left:12px;border-left:3px solid #60a5fa'>", unsafe_allow_html=True)
                st.markdown("<small style='color:#7c3aed;font-weight:700'>🔀 Parallel lanes executing in parallel:</small>")
                for lane_summary in lanes:
                    st.markdown(f"<small style='color:#8b949e;font-family:monospace'>{lane_summary}</small>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)    # ── Key Decisions ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### ⚖️ Key Decisions")
    decisions = extract_key_decisions(artifacts, events)
    if not decisions:
        st.info("No approved decisions recorded.")
    else:
        for d in decisions:
            rev_label = f" · Rev {d['revision']}" if d["revision"] else ""
            with st.expander(
                f"✔ **{d['gate']}**{rev_label} — reviewed by `{d['reviewer']}`",
                expanded=False,
            ):
                if d["summary"]:
                    st.markdown(d["summary"])
                if d["notes"]:
                    st.markdown(f"_{d['notes']}_")

    # ── Key Issues Found ────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🔍 Key Issues Found")
    issues_list = extract_key_issues(artifacts, events)
    if not issues_list:
        st.success(
            "No revision requests were raised — workflow passed all gates on first attempt.",
            icon="✅",
        )
    else:
        for entry in issues_list:
            with st.expander(
                f"⚠ **{entry['stage_label']}** requested changes · `{entry['artifact_type']}`",
                expanded=False,
            ):
                if entry["issues"]:
                    st.markdown("**Issues identified:**")
                    for issue in entry["issues"]:
                        st.markdown(f"- {issue}")
                if entry["suggestions"]:
                    st.markdown("**Suggested changes:**")
                    for s in entry["suggestions"]:
                        st.markdown(f"- {s}")

    # ── Final outcome ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🏁 Final Outcome")
    by_stage = artifacts_by_stage(artifacts)
    acceptance_arts = [
        a for a in by_stage.get("PRODUCT_ACCEPTANCE_GATE", [])
        if a["type"] == "ReviewFeedback"
    ]
    if acceptance_arts:
        final_art = acceptance_arts[-1]
        meta = final_art.get("meta", {})
        decision = str(meta.get("decision", "")).upper()
        reviewer = meta.get("reviewer") or final_art.get("created_by", "—")
        version = final_art.get("version", "—")
        notes = meta.get("notes") or meta.get("comments") or meta.get("summary", "")
        checklist = meta.get("suggested_changes", [])

        if decision == "APPROVED":
            st.success(f"**APPROVED** — Revision {version} · Reviewer: {reviewer}", icon="✅")
        elif decision == "REQUEST_CHANGES":
            st.error(f"**CHANGES REQUESTED** — Revision {version} · Reviewer: {reviewer}", icon="🔴")
        else:
            st.info(f"Decision: {decision or 'Unknown'} · Revision {version} · Reviewer: {reviewer}")

        if notes:
            st.caption(notes)

        if checklist and decision == "APPROVED":
            with st.expander(f"Acceptance checklist ({len(checklist)} criteria)", expanded=False):
                for c in checklist:
                    st.markdown(f"- {c}")
    elif status == "COMPLETED":
        st.success("Workflow completed successfully. Feature accepted by Product Owner.", icon="🎉")
    else:
        st.warning(f"Workflow status: {status}")


# ── Sidebar ───────────────────────────────────────────────────────────────────


def render_sidebar(
    readme: dict,
    artifacts: list[dict],
    events: list[dict],
    snapshots: dict,
) -> str:
    """Render sidebar, return selected stage key."""
    with st.sidebar:
        st.markdown("## 🤖 AI Software Factory")
        st.markdown(f"<small style='color:{_tokens['text_muted']}'>Autonomous Delivery Simulation</small>", unsafe_allow_html=True)
        st.divider()

        active_context = detect_active_context(artifacts, events)

        # Workflow metadata
        wf_id = readme.get("workflow_id", "—")
        status = effective_workflow_status(readme, events, snapshots)
        revision = readme.get("revision_count", "—")

        st.markdown(f"**Workflow ID**")
        st.code(wf_id[:8] + "…" if len(wf_id) > 10 else wf_id, language=None)

        col1, col2 = st.columns(2)
        col1.metric("Status", status)
        col2.metric("Revisions", revision)

        if status == "ESCALATED":
            st.divider()
            st.markdown("**⚠ Action Required: Escalation**")
            escalation_reason = latest_escalation_reason(events)
            if escalation_reason:
                st.caption(escalation_reason)

            response_templates = {
                "Select a response template": "",
                "Retry with safer fix strategy": "Resume from implementation. Prefer minimal safe changes, keep public behavior stable, and prioritize fixing currently failing tests.",
                "Focus only on failing tests": "Resume from implementation and only change code paths linked to current failing tests; avoid unrelated refactors.",
                "Stabilize then optimize later": "Resume from implementation with a stabilization-first plan. Defer non-critical improvements until tests are green.",
            }
            template_choice = st.selectbox(
                "Response template",
                options=list(response_templates.keys()),
                index=0,
                key="sidebar_escalation_template",
            )
            default_response = response_templates.get(template_choice, "")
            human_response_sidebar = st.text_area(
                "Human guidance",
                value=default_response,
                key="sidebar_human_escalation_response",
                help="Explain how the team should proceed before resuming the workflow.",
            )
            if st.button("▶ Resolve escalation and resume", use_container_width=True, key="sidebar_resume_escalation"):
                if not wf_id or wf_id == "—":
                    st.error("Workflow ID missing; cannot resume this escalation.")
                elif not human_response_sidebar.strip():
                    st.error("Enter guidance before resuming the workflow.")
                else:
                    with st.spinner("Recording guidance and resuming workflow..."):
                        success, output = run_resume_from_dashboard(wf_id, human_response_sidebar.strip())
                    if success:
                        st.success("Workflow resumed.")
                        st.code(output[-1500:] if output else "Resumed", language="text")
                        load_readme.clear()
                        load_artifacts.clear()
                        load_events.clear()
                        load_snapshots.clear()
                        st.rerun()
                    else:
                        st.error("Workflow resume failed.")
                        if output:
                            st.code(output[-3000:], language="text")

        st.markdown(f"**Repo Source**  ")
        st.markdown(f"<small style='color:{_tokens['text_secondary']}'>{active_context['seed_repo_name']}</small>", unsafe_allow_html=True)
        st.markdown(f"**Scenario**  ")
        st.markdown(f"<small style='color:{_tokens['text_secondary']}'>{active_context['scenario_title']}</small>", unsafe_allow_html=True)

        st.divider()
        st.markdown("**Run New Scenario**")
        selected_seed_repo = st.selectbox(
            "Seed repo",
            options=["fake_upload_service", "simple_auth_service", "data_pipeline"],
            index=0,
            key="seed_repo_selector",
        )
        repo_url = st.text_input(
            "Git repo URL (optional)",
            value="",
            key="repo_url_input",
            help="If provided, the workflow clones this repository into the sandbox instead of using a seed repo.",
        )
        repo_ref = st.text_input(
            "Git ref (optional)",
            value="",
            key="repo_ref_input",
            help="Optional branch, tag, or commit to checkout after clone.",
        )
        if st.button("▶ Run Workflow", use_container_width=True):
            target_label = repo_url.strip() or selected_seed_repo
            with st.spinner(f"Running workflow for {target_label}..."):
                success, output = run_workflow_from_dashboard(
                    selected_seed_repo,
                    repo_url=repo_url.strip() or None,
                    repo_ref=repo_ref.strip() or None,
                )

            if success:
                st.success(f"Workflow completed for {target_label}.")
                st.code(output[-1500:] if output else "Completed", language="text")
                load_readme.clear()
                load_artifacts.clear()
                load_events.clear()
                load_snapshots.clear()
                st.rerun()
            else:
                st.error(f"Workflow failed for {target_label}.")
                if output:
                    st.code(output[-3000:], language="text")

        if st.button("⚠ Run Escalation Demo", use_container_width=True):
            with st.spinner("Running escalation demo scenario..."):
                success, output = run_escalation_demo_from_dashboard()

            if success:
                st.success("Escalation demo completed.")
                st.code(output[-1500:] if output else "Completed", language="text")
                load_readme.clear()
                load_artifacts.clear()
                load_events.clear()
                load_snapshots.clear()
                st.rerun()
            else:
                st.error("Escalation demo failed.")
                if output:
                    st.code(output[-3000:], language="text")

        st.divider()
        st.markdown("**Work Product View**")

        decisions_map = stage_decisions(events)

        # Build stage labels — expand IMPLEMENTATION/PULL_REQUEST if multi-revision
        stage_options: list[tuple[str, str, str]] = []  # (key, label, badge_html)
        for s in STAGE_ORDER:
            icon, label, _ = STAGE_META.get(s, ("•", s, ""))
            snaps = snapshots.get(s, [])
            if not snaps and s != "DONE":
                # stage didn't execute
                continue

            if s == "IMPLEMENTATION":
                for i, snap in enumerate(snaps):
                    rev = snap.get("revision", i + 1)
                    key = f"{s}__rev{rev}"
                    stage_options.append((key, f"{icon} {label} (Rev {rev})", ""))
            elif s == "PULL_REQUEST_CREATED":
                for i, snap in enumerate(snaps):
                    rev = snap.get("revision", i + 1)
                    key = f"{s}__rev{rev}"
                    stage_options.append((key, f"{icon} {label} (Rev {rev})", ""))
            elif s in REVIEW_GATES:
                dec_list = decisions_map.get(s, [])
                for i, snap in enumerate(snaps):
                    rev = snap.get("revision", i + 1)
                    key = f"{s}__rev{rev}"
                    dec = dec_list[i] if i < len(dec_list) else ""
                    badge = decision_badge(dec) if dec else ""
                    stage_options.append((key, f"{icon} {label} (Rev {rev})", badge))
            elif s == "DONE":
                stage_options.append((s, f"{icon} Done", ""))
            else:
                stage_options.append((s, f"{icon} {label}", ""))

        labels = [opt[1] for opt in stage_options]
        keys = [opt[0] for opt in stage_options]

        if not labels:
            labels = ["🎉 Done"]
            keys = ["DONE"]

        preferred_order = [
            "TEST_VALIDATION_GATE",
            "IMPLEMENTATION",
            "PULL_REQUEST_CREATED",
            "ARCHITECTURE_DESIGN",
            "PRODUCT_DEFINITION",
        ]
        default_index = max(0, len(labels) - 1)
        for preferred_stage in preferred_order:
            for index in range(len(keys) - 1, -1, -1):
                if keys[index].startswith(preferred_stage):
                    default_index = index
                    break
            if default_index != max(0, len(labels) - 1):
                break

        if status == "ESCALATED":
            for index, key in enumerate(keys):
                if key == "DONE":
                    default_index = index
                    break

        selected_label = st.selectbox(
            "Stage",
            options=labels,
            index=default_index,
            help="Defaults to the most informative stage (usually latest test/implementation), not DONE.",
        )
        selected_key = keys[labels.index(selected_label)]

    return selected_key


# ── Main area ─────────────────────────────────────────────────────────────────


def render_main(
    selected_key: str,
    readme: dict,
    artifacts: list[dict],
    events: list[dict],
    snapshots: dict,
) -> None:
    # Header
    title = get_backlog_title(artifacts)
    problem = get_backlog_problem(artifacts)

    st.markdown(f"# {title}")
    if problem:
        st.markdown(f"> {problem}")
    st.divider()

    # Top-level IA: Overview | Process | Evidence
    tab_overview, tab_process, tab_evidence = st.tabs([
        "📊 Overview",
        "🧭 Process",
        "📚 Evidence",
    ])

    with tab_overview:
        render_summary_tab(readme, artifacts, events, snapshots)

    with tab_process:
        process_graph, process_revision = st.tabs(["Workflow Graph", "Revision Insights"])
        with process_graph:
            render_workflow_graph_tab(readme, events, snapshots)
        with process_revision:
            render_revision_insights_tab(artifacts, events)

    with tab_evidence:
        evidence_execution, evidence_artifacts, evidence_events = st.tabs([
            "Execution",
            "Work Products",
            "Event Log",
        ])

        with evidence_execution:
            render_execution_tab(readme, artifacts, events)

        with evidence_artifacts:
            st.markdown("### 📄 Work Products")
            scope = st.radio(
                "Scope",
                options=["Global (all stages)", "Selected stage"],
                horizontal=True,
                index=0,
                key="work_products_scope",
            )

            by_stage = artifacts_by_stage(artifacts)

            def _render_artifact_entry(art: dict[str, Any], include_stage: bool = False) -> None:
                art_label = ARTIFACT_TYPE_LABELS.get(art["type"], art["type"])
                rev_label = f"Rev {art['version']}"
                stage_label_text = ""
                if include_stage:
                    _, stage_name, _ = STAGE_META.get(art["stage"], ("", art["stage"], ""))
                    stage_label_text = f" · {stage_name}"

                with st.expander(
                    f"**{art_label}** · {rev_label}{stage_label_text} — created by `{art['created_by']}`",
                    expanded=False,
                ):
                    highlights = artifact_highlights(art)
                    if highlights:
                        st.markdown("**Highlights**")
                        for line in highlights:
                            st.markdown(f"- {line}")
                        st.divider()
                    if art["md"]:
                        st.markdown(art["md"])
                    else:
                        st.json(art["meta"])

            if scope == "Global (all stages)":
                stages_with_artifacts = [stage for stage in STAGE_ORDER if by_stage.get(stage)]
                st.caption(f"Showing {sum(len(by_stage[s]) for s in stages_with_artifacts)} artifacts across {len(stages_with_artifacts)} stages.")

                for stage in stages_with_artifacts:
                    icon, stage_label, role = STAGE_META.get(stage, ("•", stage, ""))
                    stage_arts = sorted(
                        by_stage.get(stage, []),
                        key=lambda x: (int(x["version"]), str(x["meta"].get("created_at", ""))),
                    )
                    with st.expander(f"{icon} {stage_label} · {len(stage_arts)} artifact(s)", expanded=False):
                        if role and role != "—":
                            st.markdown(f"<div class='artifact-tag'>Agent: {role}</div>", unsafe_allow_html=True)
                        for art in stage_arts:
                            _render_artifact_entry(art)
            else:
                if "__rev" in selected_key:
                    stage_key, rev_str = selected_key.rsplit("__rev", 1)
                    target_rev = int(rev_str)
                else:
                    stage_key = selected_key
                    target_rev = None

                icon, stage_label, role = STAGE_META.get(stage_key, ("•", stage_key, ""))
                st.markdown(f"### {icon} {stage_label}")
                if role and role != "—":
                    st.markdown(
                        f'<div class="artifact-tag">Agent: {role}</div>',
                        unsafe_allow_html=True,
                    )

                stage_arts = by_stage.get(stage_key, [])
                if target_rev is not None:
                    stage_arts = [a for a in stage_arts if a["version"] == target_rev]

                if stage_key == "DONE":
                    final_status = effective_workflow_status(readme, events, snapshots)
                    if final_status == "COMPLETED":
                        st.success("✅ Workflow completed successfully. All gates approved.", icon="🎉")
                    elif final_status == "FAILED":
                        st.error("❌ Workflow ended in FAILED status.")
                    elif final_status == "ESCALATED":
                        st.warning("⚠️ Workflow has been escalated and requires your review and decision.")
                    else:
                        st.info(f"Workflow terminal status: {final_status}")

                if not stage_arts:
                    st.info("No artifacts recorded for this stage.")
                else:
                    for art in sorted(stage_arts, key=lambda x: (int(x["version"]), str(x["meta"].get("created_at", "")))):
                        _render_artifact_entry(art)

        with evidence_events:
            st.markdown("### Event Stream")
            if not events:
                st.info("No events recorded.")
                return

            col_filter, col_search = st.columns([3, 2])
            unique_types = sorted({e.get("event_type", "") for e in events})
            selected_types = col_filter.multiselect(
                "Filter by event type",
                options=unique_types,
                default=unique_types,
            )
            search_term = col_search.text_input("Search payload", "")

            filtered = [
                e for e in events
                if e.get("event_type") in selected_types
                and (not search_term or search_term.lower() in json.dumps(e).lower())
            ]

            st.markdown(f"<small style='color:#8b949e'>{len(filtered)} events shown</small>", unsafe_allow_html=True)
            st.divider()

            for evt in filtered:
                etype = evt.get("event_type", "")
                icon = EVENT_ICONS.get(etype, "•")
                payload = evt.get("payload", {})
                ts = evt.get("timestamp", "")
                ts_short = ts[:19].replace("T", " ") if ts else ""

                summary_parts = []
                for key in ("stage", "from_stage", "to_stage", "artifact_type", "decision", "reason"):
                    if key in payload:
                        summary_parts.append(f"{key}: **{payload[key]}**")

                summary = "  ·  ".join(summary_parts) if summary_parts else json.dumps(payload)[:80]

                st.markdown(
                    f'<div class="evt">'
                    f'{icon} <strong>{etype}</strong>&nbsp;&nbsp;'
                    f'{summary}'
                    f'<br><span class="evt-time">{ts_short}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    if not DEMO_OUTPUT.exists():
        st.error(
            "No demo output found. Run the workflow engine first:\n\n"
            "```\nSet-Location autonomous_delivery\n"
            "$env:PYTHONPATH='src'\n"
            "python -m ai_software_factory\n```"
        )
        return

    readme = load_readme()
    artifacts = load_artifacts()
    events = load_events()
    snapshots = load_snapshots()

    if not artifacts:
        st.warning("Demo output directory exists but contains no artifacts yet.")
        return

    selected_key = render_sidebar(readme, artifacts, events, snapshots)
    render_main(selected_key, readme, artifacts, events, snapshots)

    # Refresh button at bottom of sidebar
    with st.sidebar:
        st.divider()
        if st.button("🔄 Refresh data"):
            load_readme.clear()
            load_artifacts.clear()
            load_events.clear()
            load_snapshots.clear()
            st.rerun()


if __name__ == "__main__" or True:
    main()
