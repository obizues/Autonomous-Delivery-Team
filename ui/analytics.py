"""
Analytics and insight-derivation helpers.
No Streamlit imports — results are consumed by render functions in app.py.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from config import ARTIFACT_TYPE_LABELS, REVIEW_GATES, STAGE_META, STAGE_ORDER
from query import (
    artifacts_by_stage,
    first_artifact,
    latest_artifact,
    list_added,
    stage_decisions,
)


# ── Event-level analytics ────────────────────────────────────────────────────


def planner_insights_by_revision(events: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("event_type") != "CHANGE_PLAN_GENERATED":
            continue
        payload = event.get("payload", {})
        revision = payload.get("revision")
        if not isinstance(revision, int):
            continue
        grouped[revision].append({
            "summary":           payload.get("summary", ""),
            "confidence":        payload.get("confidence", "UNKNOWN"),
            "files_to_modify":   payload.get("files_to_modify", []),
            "target_symbols":    payload.get("target_symbols", {}),
            "target_confidence": payload.get("target_confidence", {}),
            "intent_category":   payload.get("intent_category", "GENERAL"),
        })
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
        grouped[revision].append({
            "event_type": event_type,
            "file_path":  payload.get("file_path", "unknown"),
            "operation":  payload.get("operation", "unknown"),
            "symbols":    payload.get("symbols", []),
            "message":    payload.get("message", ""),
        })
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

    start_stage = transitions[0].get("payload", {}).get("from_stage", "BACKLOG_INTAKE")
    nodes: list[dict] = [{"stage": start_stage, "revision": 1, "loop_entry": False}]

    prev_revision = 1
    for transition in transitions:
        payload = transition.get("payload", {})
        to_stage = payload.get("to_stage", "")
        next_revision = payload.get("revision", prev_revision)
        if not isinstance(next_revision, int):
            next_revision = prev_revision
        loop_entry = to_stage == "IMPLEMENTATION" and next_revision > prev_revision
        nodes.append({"stage": to_stage, "revision": next_revision, "loop_entry": loop_entry})
        prev_revision = next_revision

    return nodes


# ── Summary-level analytics ───────────────────────────────────────────────────


def build_stage_timeline(
    artifacts: list[dict],
    events: list[dict],
    snapshots: dict,
) -> list[dict]:
    """One row per executed stage (revision-aware)."""
    decisions_map = stage_decisions(events)
    by_stage = artifacts_by_stage(artifacts)
    rows = []

    for s in STAGE_ORDER:
        snaps = snapshots.get(s, [])
        icon, label, role = STAGE_META.get(s, ("•", s, ""))

        if s == "DONE":
            rows.append({
                "stage": s, "label": label, "icon": icon, "role": role,
                "artifact_types": [], "decision": "COMPLETED",
                "is_gate": False, "revision": None,
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
                "stage":          s,
                "label":          f"{label} (Rev {rev})" if multi else label,
                "icon":           icon,
                "role":           role,
                "artifact_types": art_types,
                "decision":       dec,
                "is_gate":        s in REVIEW_GATES,
                "revision":       rev,
            })
    return rows


def extract_key_decisions(artifacts: list[dict], events: list[dict]) -> list[dict]:
    """For each approved review gate, return a structured summary entry."""
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
                "gate":     gate_label,
                "reviewer": meta.get("reviewer", meta.get("created_by", "")),
                "summary":  meta.get("comments", meta.get("summary", "")),
                "notes":    meta.get("notes", ""),
                "revision": art["version"],
            })

    gate_order_index = {
        "Architecture Review": 0,
        "Peer Code Review":    1,
        "Test Validation":     2,
        "Product Acceptance":  3,
    }
    result.sort(key=lambda item: (
        gate_order_index.get(str(item.get("gate", "")), 999),
        int(item.get("revision", 0) or 0),
    ))
    return result


def extract_key_issues(artifacts: list[dict], events: list[dict]) -> list[dict]:
    """Find REQUEST_CHANGES decisions and pull issues + suggested_changes."""
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
        review_feedback = sorted(
            [a for a in by_stage.get(stage, []) if a.get("type") == "ReviewFeedback"],
            key=lambda a: (
                int(a.get("version", 1) or 1),
                str(a.get("meta", {}).get("created_at", "")),
                str(a.get("uuid", "")),
            ),
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
                    a for a in by_stage.get(stage, [])
                    if a.get("type") == "TestResult"
                    and int(a.get("version", 1) or 1) == revision
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
                result.append({
                    "stage_label":   label,
                    "gate":          stage,
                    "artifact_type": artifact_type_label,
                    "issues":        issues,
                    "suggestions":   suggestions,
                    "revision":      revision,
                })

    result.sort(key=lambda item: (
        STAGE_ORDER.index(item["gate"]) if item["gate"] in STAGE_ORDER else 999,
        int(item.get("revision", 0) or 0),
    ))
    return result


def detect_revision_cycles(events: list[dict]) -> list[dict]:
    """Detect revision loops from REVISION_STARTED events."""
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

        cycles.append({
            "gate":            stage,
            "failed_revision": failed_revision,
            "next_revision":   next_revision,
            "decision":        "REQUEST_CHANGES",
            "decision_notes":  decision_notes,
        })
    return cycles


def infer_cycle_reason(cycle: dict, artifacts: list[dict]) -> dict:
    gate = cycle["gate"]
    failed_revision = cycle["failed_revision"]

    feedback = first_artifact(artifacts, gate, failed_revision, "ReviewFeedback")
    test_result = first_artifact(artifacts, gate, failed_revision, "TestResult")

    summary = ""
    issues: list[str] = []

    if feedback:
        m = feedback.get("meta", {})
        summary = m.get("comments") or m.get("summary") or summary
        issues.extend(m.get("issues_identified", []))

    if test_result:
        m = test_result.get("meta", {})
        failing_tests = m.get("failing_tests", [])
        if failing_tests:
            issues.extend([f"Failing test: {name}" for name in failing_tests])
        details = m.get("details", [])
        if details and len(issues) < 6:
            issues.extend(details[: max(0, 6 - len(issues))])

    if not summary:
        summary = cycle.get("decision_notes") or "Gate requested changes due to validation or review findings."

    return {"summary": summary, "issues": issues}


def infer_next_revision_changes(cycle: dict, artifacts: list[dict]) -> dict:
    failed_revision = cycle["failed_revision"]
    next_revision = cycle["next_revision"]

    impl_prev = first_artifact(artifacts, "IMPLEMENTATION", failed_revision, "CodeImplementation")
    impl_next = first_artifact(artifacts, "IMPLEMENTATION", next_revision, "CodeImplementation")
    pr_prev = first_artifact(artifacts, "PULL_REQUEST_CREATED", failed_revision, "PullRequest")
    pr_next = first_artifact(artifacts, "PULL_REQUEST_CREATED", next_revision, "PullRequest")
    tests_prev = first_artifact(artifacts, "TEST_VALIDATION_GATE", failed_revision, "TestResult")
    tests_next = first_artifact(artifacts, "TEST_VALIDATION_GATE", next_revision, "TestResult")
    arch_prev = first_artifact(artifacts, "ARCHITECTURE_REVIEW_GATE", failed_revision, "ReviewFeedback")
    arch_next = first_artifact(artifacts, "ARCHITECTURE_REVIEW_GATE", next_revision, "ReviewFeedback")

    implementation_changes: list[str] = []
    if impl_prev and impl_next:
        prev_files = impl_prev.get("meta", {}).get("files_changed", [])
        next_files = impl_next.get("meta", {}).get("files_changed", [])
        added_files = list_added(prev_files, next_files)
        if added_files:
            implementation_changes.extend([f"Added/updated: {f}" for f in added_files[:6]])
        prev_summary = impl_prev.get("meta", {}).get("summary", "")
        next_summary = impl_next.get("meta", {}).get("summary", "")
        if next_summary and next_summary != prev_summary:
            implementation_changes.append(next_summary)
    elif impl_next:
        implementation_changes.append(
            impl_next.get("meta", {}).get("summary", "Implementation updated in next revision.")
        )

    additional_tests: list[str] = []
    if tests_prev and tests_next:
        pm = tests_prev.get("meta", {})
        nm = tests_next.get("meta", {})
        prev_tests = pm.get("unit_tests", []) + pm.get("integration_tests", [])
        next_tests = nm.get("unit_tests", []) + nm.get("integration_tests", [])
        new_tests = list_added(prev_tests, next_tests)
        if new_tests:
            additional_tests.extend([f"Added test: {t}" for t in new_tests[:6]])
        prev_failed = int(pm.get("failed_cases", 0))
        next_failed = int(nm.get("failed_cases", 0))
        if next_failed < prev_failed:
            additional_tests.append(f"Failed tests reduced from {prev_failed} to {next_failed}.")
        coverage_estimate = nm.get("coverage_estimate")
        if coverage_estimate:
            additional_tests.append(f"Validation result: {coverage_estimate}")

    architecture_adjustments: list[str] = []
    if pr_prev and pr_next:
        prev_pr_files = pr_prev.get("meta", {}).get("files_modified", [])
        next_pr_files = pr_next.get("meta", {}).get("files_modified", [])
        pr_deltas = list_added(prev_pr_files, next_pr_files)
        if pr_deltas:
            architecture_adjustments.extend([f"Pull request scope expanded: {f}" for f in pr_deltas[:5]])
    if arch_prev and arch_next:
        prev_notes = arch_prev.get("meta", {}).get("comments", "")
        next_notes = arch_next.get("meta", {}).get("comments", "")
        if next_notes and next_notes != prev_notes:
            architecture_adjustments.append("Architecture review notes were updated and re-approved.")

    return {
        "implementation_changes": implementation_changes,
        "additional_tests":       additional_tests,
        "architecture_adjustments": architecture_adjustments,
    }


# ── Artifact display analytics ────────────────────────────────────────────────


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
            lines.append(f"pytest status: {'PASSED' if passed else 'FAILED'}")
        if isinstance(failed_cases, int) and isinstance(total_cases, int):
            lines.append(f"Test cases: {total_cases} total, {failed_cases} failing")
        failing_tests = meta.get("failing_tests", [])
        if isinstance(failing_tests, list) and failing_tests:
            lines.append(f"Failing tests: {', '.join(str(t) for t in failing_tests[:3])}")

    files_changed = meta.get("files_changed", [])
    if isinstance(files_changed, list) and files_changed:
        lines.append(f"Files changed: {', '.join(str(f) for f in files_changed[:3])}")

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
