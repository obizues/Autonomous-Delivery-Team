"""
AI Software Factory — Streamlit Dashboard
Run with:
  streamlit run ui/app.py
from the autonomous_delivery directory.
"""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from actions import (
    latest_escalation_reason,
    run_escalation_demo_from_dashboard,
    run_resume_from_dashboard,
    run_workflow_from_dashboard,
)
from analytics import (
    artifact_highlights,
    build_graph_nodes,
    build_stage_timeline,
    cross_review_assignments_by_revision,
    detect_revision_cycles,
    engineer_lane_insights_by_revision,
    extract_key_decisions,
    extract_key_issues,
    infer_cycle_reason,
    infer_next_revision_changes,
    merge_conflict_gate_outcomes,
    patch_events_by_revision,
    planner_insights_by_revision,
)
from config import (
    ARTIFACT_TYPE_LABELS,
    DEMO_OUTPUT,
    EVENT_ICONS,
    REVIEW_GATES,
    STAGE_META,
    STAGE_ORDER,
    TOKENS,
)
from loader import load_artifacts, load_events, load_readme, load_snapshots
from query import (
    artifacts_by_stage,
    count_decisions,
    decision_badge,
    detect_active_context,
    effective_workflow_status,
    first_artifact,
    get_backlog_problem,
    get_backlog_title,
    latest_artifact,
    latest_snapshot,
    stage_decisions,
    team_overview,
)

# Alias so all inline HTML f-strings continue to work unchanged
_tokens = TOKENS

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Software Factory",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


# ── Tab renderers ─────────────────────────────────────────────────────────────


def render_workflow_graph_tab(readme: dict, events: list[dict], snapshots: dict) -> None:
    st.markdown("### 🧭 Workflow Graph")
    st.markdown(
        "Visual path of the current run, including review decisions and revision loops."
    )

    # Surface latest human escalation decision in process view for traceability
    artifact_items = load_artifacts()
    _render_human_intervention_card(artifact_items)

    nodes = build_graph_nodes(events)
    if not nodes:
        st.info("No transition data found yet. Run the workflow to generate graph data.")
        return

    decision_map = stage_decisions(events)
    stage_counts: dict[str, int] = {}
    for node in nodes:
        stage_counts[node["stage"]] = stage_counts.get(node["stage"], 0) + 1

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

    decision_index: dict[str, int] = {}

    for index, node in enumerate(nodes):
        stage = node["stage"]
        revision = node["revision"]
        icon, _, _ = STAGE_META.get(stage, ("•", stage, ""))

        show_revision = stage_counts.get(stage, 0) > 1 or stage in {
            "IMPLEMENTATION",
            "PULL_REQUEST_CREATED",
            "MERGE_CONFLICT_GATE",
            "ARCHITECTURE_REVIEW_GATE",
            "PEER_CODE_REVIEW_GATE",
            "TEST_VALIDATION_GATE",
            "PRODUCT_ACCEPTANCE_GATE",
        }
        title = f"{stage} (Rev {revision})" if show_revision else stage

        decision = ""
        if stage in REVIEW_GATES:
            decision_list = decision_map.get(stage, [])
            dec_idx = decision_index.get(stage, 0)
            if dec_idx < len(decision_list):
                decision = decision_list[dec_idx]
            decision_index[stage] = dec_idx + 1

        is_last = index == len(nodes) - 1
        if is_last and stage == current_stage and stage != "DONE":
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


def _latest_human_intervention(artifacts: list[dict]) -> dict[str, Any] | None:
    interventions = [a for a in artifacts if a.get("type") == "HumanIntervention"]
    if not interventions:
        return None
    return max(
        interventions,
        key=lambda a: (
            int(a.get("version", 0) or 0),
            str(a.get("meta", {}).get("created_at", "")),
            str(a.get("uuid", "")),
        ),
    )


def _render_human_intervention_card(artifacts: list[dict], title: str = "🧑‍💼 Escalation Decision") -> None:
    intervention = _latest_human_intervention(artifacts)
    if intervention is None:
        return

    meta = intervention.get("meta", {})
    responder = str(meta.get("responder") or intervention.get("created_by") or "human_operator")
    resume_stage = str(meta.get("resume_stage") or "IMPLEMENTATION")
    response_template = str(meta.get("response_template") or "")
    human_guidance = str(meta.get("response") or "")
    resume_max_steps = meta.get("resume_max_steps")

    max_rejections = "?"
    if isinstance(resume_max_steps, int):
        max_rejections = str(max(1, (resume_max_steps - 15) // 8))

    st.markdown(f"#### {title}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Responder", responder)
    m2.metric("Resume Stage", resume_stage)
    m3.metric("Max Rejections", max_rejections)
    if response_template:
        st.markdown(f"**Response Template:** {response_template}")
    if human_guidance:
        st.info(human_guidance)


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

    _render_human_intervention_card(artifacts)

    lane_insights = engineer_lane_insights_by_revision(events)
    cross_reviews = cross_review_assignments_by_revision(artifacts)
    merge_gate = merge_conflict_gate_outcomes(artifacts)

    latest_engineer_revision: int | None = None
    if lane_insights:
        latest_engineer_revision = max(lane_insights.keys())

    if latest_engineer_revision is not None:
        lane_rows = lane_insights.get(latest_engineer_revision, [])
        review_lookup = {
            row["lane_id"]: row.get("reviewed_by", "—")
            for row in cross_reviews.get(latest_engineer_revision, [])
        }
        st.markdown(f"#### 👷 Engineer Agents · Revision {latest_engineer_revision}")
        for row in lane_rows:
            lane_id = str(row.get("lane_id", "unknown"))
            story_slice = str(row.get("story_slice", "Unspecified slice"))
            files = row.get("files", [])
            applied = int(row.get("applied", 0) or 0)
            failed = int(row.get("failed", 0) or 0)
            reviewed_by = review_lookup.get(lane_id, "—")
            status = "✅" if failed == 0 else "❌"
            st.markdown(
                f"- **{lane_id}** · slice: {story_slice} · reviewed by `{reviewed_by}` · {status} applied={applied} failed={failed}"
            )
            st.caption(
                "Files: " + (", ".join(str(file_name) for file_name in files) if files else "(none)")
            )

        merge_outcome = merge_gate.get(latest_engineer_revision)
        if merge_outcome:
            decision = str(merge_outcome.get("decision", ""))
            reviewer = str(merge_outcome.get("reviewer", "merge_conflict_guard"))
            if decision == "APPROVED":
                st.success(f"Merge Conflict Gate: APPROVED by {reviewer}")
            elif decision == "REQUEST_CHANGES":
                st.error(f"Merge Conflict Gate: REQUEST_CHANGES by {reviewer}")
            else:
                st.info(f"Merge Conflict Gate decision: {decision or 'UNKNOWN'}")

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
    lane_insights = engineer_lane_insights_by_revision(events)
    latest_lane_revision = max(lane_insights.keys()) if lane_insights else None
    latest_lane_rows = lane_insights.get(latest_lane_revision, []) if latest_lane_revision is not None else []
    engineer_lane_count = len(latest_lane_rows)
    engineer_lane_ids = [str(row.get("lane_id", "")) for row in latest_lane_rows if row.get("lane_id")]
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
                <span style="color:{_tokens['text_secondary']};font-size:0.85rem">👷&nbsp;Engineer agents: <strong>{engineer_lane_count}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_human_intervention_card(artifacts)

    # ── Team overview ───────────────────────────────────────────────────────
    with st.expander("👥 Autonomous Delivery Team", expanded=False):
        team_rows = team_overview(snapshots)
        cols = st.columns(5)
        for col, row in zip(cols, team_rows):
            role_label = str(row["role"])
            if role_label == "Engineer":
                role_label = "Engineer Team"
            col.markdown(f"**{role_label}**")
            status_text = str(row["status"])
            if row["role"] == "Engineer" and engineer_lane_count > 0:
                cycles = int(row.get("cycles", 0) or 0)
                revision_label = "revision" if cycles == 1 else "revisions"
                engineer_label = "engineer agent" if engineer_lane_count == 1 else "engineer agents"
                if cycles > 0:
                    status_text = f"{engineer_lane_count} {engineer_label} active across {cycles} {revision_label}"
                else:
                    status_text = f"{engineer_lane_count} {engineer_label} active"
            col.markdown(f"<small style='color:#8b949e'>{status_text}</small>", unsafe_allow_html=True)
            col.caption(f"Last: {row['last_stage']}")
            if row["role"] == "Engineer" and engineer_lane_ids:
                col.caption("Engineers: " + ", ".join(engineer_lane_ids))

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
        with st.expander("🔀 Engineer Agents and Parallel Lanes", expanded=False):
            st.markdown(f"**{len(engineer_lanes)} engineer agents working across parallel lanes** on decomposed tasks:")
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

    lane_insights = engineer_lane_insights_by_revision(events)
    cross_reviews = cross_review_assignments_by_revision(artifacts)
    merge_gate = merge_conflict_gate_outcomes(artifacts)

    engineer_revisions = set(lane_insights.keys()) | set(cross_reviews.keys()) | set(merge_gate.keys())
    latest_engineer_revision = max(engineer_revisions) if engineer_revisions else None

    if latest_engineer_revision is not None:
        with st.expander("🧑‍💻 Engineer Control Tower", expanded=False):
            lane_rows = lane_insights.get(latest_engineer_revision, [])
            review_rows = cross_reviews.get(latest_engineer_revision, [])
            review_lookup = {row["lane_id"]: row.get("reviewed_by", "—") for row in review_rows}

            total_files = sum(len(row.get("files", [])) for row in lane_rows)
            total_applied = sum(int(row.get("applied", 0) or 0) for row in lane_rows)
            total_failed = sum(int(row.get("failed", 0) or 0) for row in lane_rows)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Revision", latest_engineer_revision)
            m2.metric("Engineer Agents", len(lane_rows))
            m3.metric("Files Assigned", total_files)
            m4.metric("Patch Outcome", f"{total_applied}/{total_failed}")

            if lane_rows:
                st.markdown("**Lane ownership and review routing**")
                for row in lane_rows:
                    lane_id = str(row.get("lane_id", "unknown"))
                    story_slice = str(row.get("story_slice", "Unspecified slice"))
                    reviewed_by = review_lookup.get(lane_id, "—")
                    files = row.get("files", [])
                    st.markdown(f"- **{lane_id}** · {story_slice} · reviewed by `{reviewed_by}`")
                    st.caption(
                        "Files: " + (", ".join(str(file_name) for file_name in files) if files else "(none)")
                    )

            if review_rows:
                st.markdown("**Cross-review matrix**")
                for row in review_rows:
                    st.markdown(f"- `{row['reviewed_by']}` reviews `{row['lane_id']}`")

            merge_outcome = merge_gate.get(latest_engineer_revision)
            if merge_outcome:
                decision = str(merge_outcome.get("decision", ""))
                reviewer = str(merge_outcome.get("reviewer", "merge_conflict_guard"))
                if decision == "APPROVED":
                    st.success(f"Merge Conflict Gate: APPROVED by {reviewer}")
                elif decision == "REQUEST_CHANGES":
                    st.error(f"Merge Conflict Gate: REQUEST_CHANGES by {reviewer}")
                else:
                    st.info(f"Merge Conflict Gate decision: {decision or 'UNKNOWN'}")

                issues = merge_outcome.get("issues", [])
                suggestions = merge_outcome.get("suggestions", [])
                if issues:
                    st.markdown("**Conflict findings**")
                    for issue in issues:
                        st.markdown(f"- {issue}")
                if suggestions:
                    st.markdown("**Recommended fixes**")
                    for suggestion in suggestions:
                        st.markdown(f"- {suggestion}")

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
            role_label = str(row["role"])
            if (
                row.get("stage") in {"IMPLEMENTATION", "PULL_REQUEST_CREATED", "MERGE_CONFLICT_GATE", "PEER_CODE_REVIEW_GATE"}
                and row.get("revision") in lanes_by_revision
            ):
                role_label = f"Engineer Team ({len(lanes_by_revision[row['revision']])} parallel lanes)"
            c2.markdown(
                f"<span style='color:#8b949e'>{role_label}</span>",
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
                st.markdown("<small style='color:#7c3aed;font-weight:700'>🔀 Parallel lanes executing in parallel:</small>", unsafe_allow_html=True)
                for lane_summary in lanes:
                    st.markdown(f"<small style='color:#8b949e;font-family:monospace'>{lane_summary}</small>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Key Decisions ───────────────────────────────────────────────────────
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
    st.markdown("#### 🔍 Issue History")
    issues_list = extract_key_issues(artifacts, events)
    if not issues_list:
        st.success(
            "No revision requests were raised — workflow passed all gates on first attempt.",
            icon="✅",
        )
    else:
        if status == "COMPLETED":
            st.info("These are historical issues that were raised earlier and resolved during later revisions.")
        elif status == "ESCALATED":
            st.warning("These issues are still relevant to the current escalated state.")
        else:
            st.caption("This section shows revision history, including prior resolved issues.")
        for entry in issues_list:
            with st.expander(
                f"🕘 **{entry['stage_label']}** requested changes · `{entry['artifact_type']}`",
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
    escalation_reason = latest_escalation_reason(events) if status == "ESCALATED" else None
    if escalation_reason:
        st.warning(f"⚠️ Escalated: {escalation_reason}")

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

        if checklist:
            marker = "✅" if decision == "APPROVED" else "❌" if decision == "REQUEST_CHANGES" else "⚠️"
            title = (
                f"Acceptance checklist ({len(checklist)} criteria)"
                if decision == "APPROVED"
                else f"Outstanding criteria ({len(checklist)})"
            )
            with st.expander(title, expanded=False):
                for c in checklist:
                    st.markdown(f"- {marker} {c}")
    elif status == "COMPLETED":
        st.success("Workflow completed successfully. Feature accepted by Product Owner.", icon="🎉")
    else:
        st.warning(f"Workflow status: {status}")

    _render_human_intervention_card(artifacts, title="🧑‍💼 Escalation Decision (Latest)")


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
                "Target failing tests only": "Resume from implementation and only change code paths linked to currently failing tests. Avoid unrelated refactors.",
                "Minimal safe patch set": "Resume from implementation with the smallest safe patch set that restores test stability.",
                "Stabilize first, optimize later": "Resume from implementation with a stabilization-first plan. Defer non-critical improvements until all tests are green.",
                "Custom guidance": "",
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

            resume_stage_option = st.selectbox(
                "Resume stage",
                options=[
                    "IMPLEMENTATION",
                    "MERGE_CONFLICT_GATE",
                    "PEER_CODE_REVIEW_GATE",
                    "TEST_VALIDATION_GATE",
                ],
                index=0,
                key="sidebar_resume_stage",
                help="Choose where execution should resume after escalation is resolved.",
            )
            responder_name = st.text_input(
                "Responder identity",
                value="human_operator",
                key="sidebar_resume_responder",
                help="Recorded on the HumanIntervention artifact.",
            )
            resume_max_rejections = st.number_input(
                "Max additional rejections",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
                key="sidebar_resume_max_steps",
                help=(
                    "How many more gate failures (REQUEST_CHANGES) the team is allowed before the workflow "
                    "re-escalates. Each rejection = ~6 stage transitions. 3 = ~39 steps budget."
                ),
            )
            if st.button("▶ Resolve escalation and resume", use_container_width=True, key="sidebar_resume_escalation"):
                if not wf_id or wf_id == "—":
                    st.error("Workflow ID missing; cannot resume this escalation.")
                elif not human_response_sidebar.strip():
                    st.error("Enter guidance before resuming the workflow.")
                elif not responder_name.strip():
                    st.error("Responder identity is required.")
                else:
                    with st.spinner("Recording guidance and resuming workflow..."):
                        success, output = run_resume_from_dashboard(
                            wf_id,
                            human_response_sidebar.strip(),
                            resume_stage=resume_stage_option,
                            responder=responder_name.strip(),
                            resume_max_steps=int(resume_max_rejections) * 8 + 15,
                            response_template=template_choice if template_choice != "Custom guidance" else "",
                        )
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
            by_stage = artifacts_by_stage(artifacts)

            def _render_artifact_entry(art: dict[str, Any], include_stage: bool = False) -> None:
                art_label = ARTIFACT_TYPE_LABELS.get(art["type"], art["type"])
                rev_label = f"Rev {art['version']}"
                actor_label = str(art.get("created_by", ""))
                if art.get("type") == "ReviewFeedback":
                    reviewer = str(art.get("meta", {}).get("reviewer", "")).strip()
                    if reviewer:
                        actor_label = reviewer
                stage_label_text = ""
                if include_stage:
                    _, stage_name, _ = STAGE_META.get(art["stage"], ("", art["stage"], ""))
                    stage_label_text = f" · {stage_name}"

                with st.expander(
                    f"**{art_label}** · {rev_label}{stage_label_text} — created by `{actor_label}`",
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

if __name__ == "__main__" or True:
    main()
