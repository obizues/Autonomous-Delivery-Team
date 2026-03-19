# Operations Runbook

## Runtime Modes

- Standard workflow run (`python -m ai_software_factory`)
- Dashboard-driven run (`ui/launcher.py`)
- Escalation demo (`scripts/demo_escalation.py`)
- Resume mode (`ASF_RESUME_WORKFLOW_ID` + `ASF_HUMAN_RESPONSE`)

## Key Environment Variables

- `PYTHONPATH=src`
- `ASF_SEED_REPO`
- `ASF_PERSISTENCE_BACKEND`
- `ASF_SQLITE_PATH`
- `ASF_REPO_URL` / `ASF_REPO_REF`
- `ASF_RESUME_WORKFLOW_ID` / `ASF_HUMAN_RESPONSE`
- `ASF_HUMAN_RESPONSE_TEMPLATE`
- `ASF_RESUME_STAGE` / `ASF_RESUME_RESPONDER` / `ASF_RESUME_MAX_REJECTIONS`
- `ASF_RESUME_MAX_STEPS` (legacy compatibility)
- Optional LLM: `LLM_API_KEY`, `LLM_API_PROVIDER`, `LLM_MODEL`

## E2E Resume Health Check

Run:

```powershell
python scripts/demo_resume_e2e.py
```

Expected terminal output includes `resume_e2e: PASSED`.

## Requirements Traceability

Use this quick matrix to map requirement areas from `docs/REQUIREMENTS.md` to operational verification points.

| Requirement Area | Verification Path |
| --- | --- |
| Workflow orchestration | Run `python -m ai_software_factory`; verify stage progression and decisions in `demo_output/latest/events.jsonl`. |
| Parallel engineer execution | Run `python -m ai_software_factory`; verify lane assignments, cross-review mapping, and lane outcomes in `demo_output/latest/artifacts/` and dashboard Process view. |
| Review and governance gates | Run `python scripts/demo_acceptance.py`; verify gate decisions and revision loops in terminal output and `events.jsonl`. |
| Merge conflict gate behavior | Run `python scripts/demo_acceptance.py`; confirm merge gate outcomes are present in artifacts/events and no unresolved conflict markers pass through. |
| Escalation and resume controls | Run `python scripts/demo_escalation.py` then `python scripts/demo_resume_e2e.py`; verify `ESCALATION_RAISED`, `HUMAN_FEEDBACK_RECORDED`, `WORKFLOW_RESUMED`, `REVISION_STARTED`. |
| Dashboard observability | Run `python ui/launcher.py`; verify latest run loads and engineer-lane/cross-review visibility is present. |
| Persistence and artifact integrity | Run with `ASF_PERSISTENCE_BACKEND=sqlite`; verify state in `ASF_SQLITE_PATH` and artifacts in `demo_output/latest`. |
| Release acceptance baseline | Confirm `python scripts/demo_acceptance.py` and `python scripts/demo_resume_e2e.py` both pass. |

## Troubleshooting

### Dashboard won’t load
- Verify dependencies installed from `requirements.txt`.
- Run `python ui/launcher.py --port 8600` if 8501 is busy.

### Workflow fails early
- Confirm `PYTHONPATH=src` is set.
- Validate seed repo exists under `seed_repos/`.

### Resume fails
- Ensure workflow status is `ESCALATED`.
- Verify `ASF_RESUME_WORKFLOW_ID` points to an existing workflow in persistence store.
- Ensure non-empty `ASF_HUMAN_RESPONSE`.

### No artifacts in UI
- Check `demo_output/latest` exists.
- Run a fresh workflow from launcher to regenerate output.

## Operational Signals to Monitor

- Event stream (`events.jsonl`) for `ESCALATION_RAISED`, `REVISION_STARTED`, `DECISION_MADE`.
- Gate decisions by revision.
- Merge conflict gate outcomes.
- Test result regression indicators (`new_failures`, `stable_pass_streak`).
