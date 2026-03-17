from __future__ import annotations

from typing import Any

from ai_software_factory.orchestration.runner import build_demo_backlog, create_engine


def run_scenario(seed_repo: str, label: str) -> tuple[dict[str, object], list[Any]]:
    engine = create_engine(seed_repo_name=seed_repo)
    backlog = build_demo_backlog(seed_repo)

    state = engine.start(backlog)
    final_state = engine.run_until_terminal(state.workflow_id)
    events = engine.event_bus.list_events(state.workflow_id)
    summary = {
        "status": final_state.status.value,
        "revision": final_state.revision,
        "event_count": len(events),
    }
    print(f"{label}: status={summary['status']} revision={summary['revision']} events={summary['event_count']}")
    return summary, events


def main() -> int:
    ok = True

    summary_1, _ = run_scenario("fake_upload_service", "scenario_1_success")
    if summary_1["status"] != "COMPLETED":
        ok = False
        print("scenario_1_success failed: expected COMPLETED")

    summary_2, events_2 = run_scenario("fake_upload_service", "scenario_2_semantic_signals")
    has_patch_events = any(
        event.event_type.value in {"PATCH_APPLIED", "PATCH_ROLLED_BACK"}
        for event in events_2
    )
    has_planner_fields = any(
        event.event_type.value == "CHANGE_PLAN_GENERATED"
        and "intent_category" in event.payload
        and "target_confidence" in event.payload
        for event in events_2
    )
    if summary_2["status"] != "COMPLETED" or not has_patch_events or not has_planner_fields:
        ok = False
        print(
            "scenario_2_semantic_signals failed: expected COMPLETED with patch events and planner semantic fields"
        )

    summary_3, _ = run_scenario("simple_auth_service", "scenario_3_auth_success")
    if summary_3["status"] != "COMPLETED":
        ok = False
        print("scenario_3_auth_success failed: expected COMPLETED")

    summary_4, _ = run_scenario("data_pipeline", "scenario_4_pipeline_success")
    if summary_4["status"] != "COMPLETED":
        ok = False
        print("scenario_4_pipeline_success failed: expected COMPLETED")

    if ok:
        print("acceptance: PASSED")
        return 0

    print("acceptance: FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
