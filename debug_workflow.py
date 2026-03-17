#!/usr/bin/env python3
from src.ai_software_factory.orchestration.runner import create_engine, build_demo_backlog

engine = create_engine("fake_upload_service")
backlog = build_demo_backlog("fake_upload_service")
state = engine.start(backlog)

print(f"Started workflow: {state.workflow_id}")
print(f"Initial stage: {state.current_stage}")
print()

final_state = engine.run_until_terminal(state.workflow_id)

print(f"Final status: {final_state.status.value}")
print(f"Final stage: {final_state.current_stage.value}")
print(f"Revision: {final_state.revision}")

