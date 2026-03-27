"""
Analytics and insight-derivation helpers.
No Streamlit imports — results are consumed by render functions in app.py.
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from autonomous_delivery.ui.config import STAGE_ORDER, STAGE_META, ARTIFACT_TYPE_LABELS, REVIEW_GATES
from typing import Any


from query import (
    artifacts_by_stage,
    first_artifact,
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


def engineer_lane_insights_by_revision(events: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}

    for event in events:
        if event.get("event_type") != "FILES_MODIFIED":
            continue
        payload = event.get("payload", {})
        revision = payload.get("revision")
        if not isinstance(revision, int):
            continue

        lane_rows: dict[str, dict[str, Any]] = {}

        assignments = payload.get("engineer_lane_assignments", [])
        if isinstance(assignments, list):
            for item in assignments:
                if not isinstance(item, dict):
                    continue
                lane_id = str(item.get("lane_id", "")).strip()
                if not lane_id:
                    continue
                files = item.get("files", [])
                lane_rows[lane_id] = {
                    "lane_id": lane_id,
                    "story_slice": str(item.get("story_slice", "Unspecified slice")),
                    "files": [str(file_name) for file_name in files] if isinstance(files, list) else [],
                    "applied": 0,
                    "failed": 0,
                }

        summaries = payload.get("engineer_lanes", [])
        if isinstance(summaries, list):
            for summary in summaries:
                text = str(summary)
                lane_match = re.search(r"^(engineer_\d+)\b", text)
                if not lane_match:
                    continue
                lane_id = lane_match.group(1)
                row = lane_rows.setdefault(
                    lane_id,
                    {
                        "lane_id": lane_id,
                        "story_slice": "Unspecified slice",
                        "files": [],
                        "applied": 0,
                        "failed": 0,
                    },
                )

                slice_match = re.search(r"slice=(.+?)\s+files=", text)
                if slice_match:
                    row["story_slice"] = slice_match.group(1).strip()

                files_match = re.search(r"files=(.+?)\s+applied=", text)
                if files_match:
                    try:
                        parsed_files = ast.literal_eval(files_match.group(1).strip())
                        if isinstance(parsed_files, list):
                            row["files"] = [str(file_name) for file_name in parsed_files]
                    except Exception:
                        pass

                applied_match = re.search(r"applied=(\d+)", text)
                failed_match = re.search(r"failed=(\d+)", text)
                if applied_match:
                    row["applied"] = int(applied_match.group(1))
                if failed_match:
                    row["failed"] = int(failed_match.group(1))

        grouped[revision] = sorted(
            lane_rows.values(),
            key=lambda row: (
                int(str(row["lane_id"]).split("_")[-1])
                if str(row["lane_id"]).split("_")[-1].isdigit() else 999
            ),
        )

    return grouped


def cross_review_assignments_by_revision(artifacts: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)

    for artifact in artifacts:
        if artifact.get("type") != "PullRequest":
            continue
        revision = int(artifact.get("version", 1) or 1)
        meta = artifact.get("meta", {})
        title = str(meta.get("title", ""))

        lane_match = re.search(r"\[(engineer_\d+)(?::\s*([^\]]+))?\]", title)
        if not lane_match:
            continue
        lane_id = lane_match.group(1)
        story_slice = lane_match.group(2).strip() if lane_match.group(2) else "Unspecified slice"

        reviewed_by = "—"
        linked_ids = meta.get("linked_review_ids", [])
        if isinstance(linked_ids, list):
            for item in linked_ids:
                text = str(item)
                review_match = re.search(r"(engineer_\d+)->reviews->(engineer_\d+)", text)
                if review_match and review_match.group(2) == lane_id:
                    reviewed_by = review_match.group(1)
                    break

        grouped[revision].append(
            {
                "lane_id": lane_id,
                "reviewed_by": reviewed_by,
                "story_slice": story_slice,
                "files": [str(file_name) for file_name in meta.get("files_modified", []) if isinstance(file_name, str)],
            }
        )

    result: dict[int, list[dict]] = {}
    for revision, rows in grouped.items():
        result[revision] = sorted(
            rows,
            key=lambda row: (
                int(str(row["lane_id"]).split("_")[-1])
                if str(row["lane_id"]).split("_")[-1].isdigit() else 999
            ),
        )
    return result


def merge_conflict_gate_outcomes(artifacts: list[dict]) -> dict[int, dict[str, Any]]:
    outcomes: dict[int, dict[str, Any]] = {}
    for artifact in artifacts:
        if artifact.get("stage") != "MERGE_CONFLICT_GATE" or artifact.get("type") != "ReviewFeedback":
            continue
        revision = int(artifact.get("version", 1) or 1)
        meta = artifact.get("meta", {})
        outcomes[revision] = {
            "decision": str(meta.get("decision", "")),
            "reviewer": str(meta.get("reviewer", artifact.get("created_by", ""))),
            "comments": str(meta.get("comments", "")),
            "issues": [str(item) for item in meta.get("issues_identified", []) if isinstance(item, str)],
            "suggestions": [str(item) for item in meta.get("suggested_changes", []) if isinstance(item, str)],
        }
    return outcomes


def engineer_revision_rollup(
    artifacts: list[dict],
    events: list[dict],
) -> tuple[
    dict[int, list[dict]],
    dict[int, list[dict]],
    dict[int, dict[str, Any]],
    int | None,
]:
    lane_insights = engineer_lane_insights_by_revision(events)
    cross_reviews = cross_review_assignments_by_revision(artifacts)
    merge_gate = merge_conflict_gate_outcomes(artifacts)
    engineer_revisions = set(lane_insights.keys()) | set(cross_reviews.keys()) | set(merge_gate.keys())
    latest_engineer_revision = max(engineer_revisions) if engineer_revisions else None
    return lane_insights, cross_reviews, merge_gate, latest_engineer_revision


def quality_trends_by_revision(artifacts: list[dict]) -> list[dict[str, Any]]:
    artifacts_by_stage(artifacts)  # noqa: F841
    revisions = sorted({int(a.get("version", 0) or 0) for a in artifacts if int(a.get("version", 0) or 0) > 0})
    rows: list[dict[str, Any]] = []

    def _score_from_comments(comments: str, label_pattern: str) -> float | None:
        match = re.search(label_pattern, comments)
        if not match:
            return None
        try:
            return float(match.group(1))
        except Exception:
            return None

    for revision in revisions:
        peer_feedback = first_artifact(artifacts, "PEER_CODE_REVIEW_GATE", revision, "ReviewFeedback")
        arch_feedback = first_artifact(artifacts, "ARCHITECTURE_REVIEW_GATE", revision, "ReviewFeedback")
        merge_feedback = first_artifact(artifacts, "MERGE_CONFLICT_GATE", revision, "ReviewFeedback")
        test_result = first_artifact(artifacts, "TEST_VALIDATION_GATE", revision, "TestResult")

        peer_score = None
        peer_decision = ""
        if peer_feedback:
            peer_meta = peer_feedback.get("meta", {})
            peer_decision = str(peer_meta.get("decision", ""))
            peer_score = _score_from_comments(str(peer_meta.get("comments", "")), r"Overall Score:\s*(\d+)%")

        arch_score = None
        arch_decision = ""
        if arch_feedback:
            arch_meta = arch_feedback.get("meta", {})
            arch_decision = str(arch_meta.get("decision", ""))
            arch_score = _score_from_comments(
                str(arch_meta.get("comments", "")),
                r"Overall Architecture Score:\s*(\d+)%",
            )

        failed_tests = None
        test_status = ""
        if test_result:
            test_meta = test_result.get("meta", {})
            failed_tests = int(test_meta.get("failed_cases", 0) or 0)
            passed = bool(test_meta.get("passed", False))
            test_status = "PASSED" if passed else "FAILED"

        merge_decision = ""
        merge_issue_count = 0
        if merge_feedback:
            merge_meta = merge_feedback.get("meta", {})
            merge_decision = str(merge_meta.get("decision", ""))
            merge_issue_count = len(merge_meta.get("issues_identified", []) or [])

        rows.append(
            {
                "revision": revision,
                "peer_score_pct": peer_score,
                "peer_decision": peer_decision,
                "arch_score_pct": arch_score,
                "arch_decision": arch_decision,
                "failed_tests": failed_tests,
                "test_status": test_status,
                "merge_issues": merge_issue_count,
                "merge_decision": merge_decision,
            }
        )

    return rows


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
    first_revision = transitions[0].get("payload", {}).get("revision", 1)
    if not isinstance(first_revision, int) or first_revision <= 0:
        first_revision = 1
    nodes: list[dict] = [{"stage": start_stage, "revision": first_revision, "loop_entry": False}]

    prev_revision = first_revision
    for transition in transitions:
        payload = transition.get("payload", {})
        to_stage = payload.get("to_stage", "")
        next_revision = payload.get("revision", prev_revision)
        if not isinstance(next_revision, int):
            next_revision = prev_revision
        loop_entry = next_revision > prev_revision
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
        "MERGE_CONFLICT_GATE":      "Merge Conflict Gate",
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
        "Merge Conflict Gate": 0,
        "Architecture Review": 1,
        "Peer Code Review":    2,
        "Test Validation":     3,
        "Product Acceptance":  4,
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
        "MERGE_CONFLICT_GATE",
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
        trigger_stage = event.get("stage", "")
        payload = event.get("payload", {})
        next_revision = payload.get("new_revision")
        if not isinstance(next_revision, int) or next_revision <= 1:
            continue

        failed_revision = payload.get("old_revision")
        if not isinstance(failed_revision, int) or failed_revision <= 0:
            failed_revision = next_revision - 1

        trigger_reason = str(payload.get("reason", ""))
        trigger_type = "HUMAN_RESUME" if trigger_reason.startswith("Human intervention resume") else "GATE_RETRY"

        gate = trigger_stage
        decision_notes = ""
        for prior in reversed(events[:index]):
            if prior.get("event_type") != "DECISION_MADE":
                continue
            prior_payload = prior.get("payload", {})
            if prior_payload.get("decision") != "REQUEST_CHANGES":
                continue
            prior_revision = prior_payload.get("revision")
            if isinstance(prior_revision, int) and prior_revision != failed_revision:
                continue
            gate = prior.get("stage", "") or prior_payload.get("stage", "") or gate
            decision_notes = prior_payload.get("notes", "")
            break

        cycles.append({
            "gate":            gate,
            "trigger_stage":   trigger_stage,
            "failed_revision": failed_revision,
            "next_revision":   next_revision,
            "decision":        "REQUEST_CHANGES",
            "decision_notes":  decision_notes,
            "trigger_reason":  trigger_reason,
            "trigger_type":    trigger_type,
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
