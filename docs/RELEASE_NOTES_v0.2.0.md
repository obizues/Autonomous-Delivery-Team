# Release Notes — v0.2.0

Release date: 2026-03-19

## Highlights

- Human escalation decisions are now first-class evidence via `HumanIntervention` metadata and dashboard cards.
- Resume policy semantics now support a rejection-based runway model (mapped to step budget internally).
- Review gates were hardened:
  - Peer code review now uses stricter weighted scoring and revision-aware thresholds.
  - Architecture review now performs implementation-to-architecture alignment checks.
- Resume reliability and observability improved:
  - Dashboard resume auto-selects the correct SQLite store by workflow ID.
  - Escalation reason is shown in final outcome and DONE-stage status views.

## Included Workflow Enhancements

- `HumanIntervention` captures:
  - response template selected,
  - human guidance,
  - resume stage,
  - responder identity,
  - resume max steps (displayed as approximate rejection runway in UI).
- Revision loop safety includes explicit escalation when revision budget is exhausted at review gates.

## Dashboard UX Updates

- Escalation Decision card appears across multiple screens:
  - Overview,
  - Process (Workflow Graph),
  - Evidence (Execution),
  - Final Outcome section.
- Escalation status now includes explicit reason text in final outcome surfaces.
- Engineer team overview correctly resolves last activity with Engineer Team stage labels.

## Compatibility Notes

- Existing env var `ASF_RESUME_MAX_STEPS` remains supported.
- New recommended control: `ASF_RESUME_MAX_REJECTIONS`.
- Existing demo scenarios remain compatible and pass acceptance validation.

## Validation Snapshot

- `python scripts/demo_acceptance.py` → `acceptance: PASSED`
- `python scripts/demo_resume_e2e.py` → `resume_e2e: PASSED`
