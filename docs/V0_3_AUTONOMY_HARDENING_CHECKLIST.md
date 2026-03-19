# v0.3 Autonomy Hardening Checklist

## Purpose

Translate the v0.2.0 baseline into a more reliable autonomous delivery system that converges under escalation/resume scenarios without repeated dead-end loops.

## Success Criteria (v0.3 Exit)

- Resume flows no longer repeatedly re-escalate because of invalid resume-stage preconditions.
- Gate policies are configurable (not hard-coded) and traceably applied per run.
- At least one additional escalation mode is implemented and validated.
- Dashboard exposes policy, rationale, and convergence metrics clearly for each revision.
- Acceptance + resume E2E demos pass with deterministic outcomes.

## Priority 1 — Resume Reliability and Convergence

- [ ] Add resume-stage precondition validation before workflow resume.
  - If required artifacts for chosen stage are missing, auto-adjust to a safe upstream stage or block with actionable reason.
- [ ] Add stage fallback mapping for resume requests.
  - Example: `MERGE_CONFLICT_GATE` fallback to `PULL_REQUEST_CREATED` when no PR artifacts exist for target revision.
- [ ] Persist and surface resume-decision rationale.
  - Record why requested stage was accepted/adjusted/rejected.
- [ ] Prevent immediate re-escalation loops on unchanged failure signatures.
  - Add policy guard requiring a material change signal (artifacts/tests/patches) before counting a retry attempt.

## Priority 2 — Policy Externalization

- [ ] Introduce external gate-policy configuration file (YAML/JSON).
  - Thresholds, revision budget, rejection runway, escalation triggers, gate-specific conditions.
- [ ] Add policy versioning and run-time policy snapshot capture.
  - Persist effective policy with each workflow run for audit and reproducibility.
- [ ] Add policy validation + startup diagnostics.
  - Fail fast on invalid policy schemas and conflicting settings.

## Priority 3 — Escalation Modes

- [ ] Implement **Abandon** escalation mode.
  - Marks workflow terminal with explicit non-recoverable status and reason taxonomy.
- [ ] Implement **Best Effort** escalation mode.
  - Produces constrained deliverable package (known issues + mitigation + recommendation) without claiming full acceptance.
- [ ] Add operator mode selector in dashboard resume/escalation controls.

## Priority 4 — Quality Scorecards and Telemetry

- [ ] Add run-level autonomy scorecard.
  - Convergence rate, revisions-to-completion, re-escalation count, unresolved issue carryover.
- [ ] Add gate health scorecard.
  - Per-gate approval rate, repeat-failure patterns, false-progress indicators.
- [ ] Add revision delta quality signal to dashboard summaries.
  - Show whether each revision materially reduced risk/failures.

## Priority 5 — UI and Codebase Maintainability

- [ ] Extract additional data-shaping logic from `ui/app.py` into `ui/analytics.py` / `ui/query.py`.
- [ ] Consolidate revision and cycle formatting helpers for all tabs.
- [ ] Add focused regression checks for UI-level revision consistency across graph/summary/execution/sidebar.

## Test Plan for v0.3

- [ ] Extend `scripts/demo_resume_e2e.py` with scenarios:
  - valid resume-stage path,
  - invalid resume-stage auto-fallback,
  - abandon mode,
  - best-effort mode.
- [ ] Add deterministic checks for policy externalization.
- [ ] Add telemetry assertions for revision/cycle counters and escalation mode outcomes.

## Definition of Done

- [ ] All v0.3 checklist items marked complete.
- [ ] `scripts/demo_acceptance.py` and `scripts/demo_resume_e2e.py` green.
- [ ] Documentation updated (`README.md`, `docs/OPERATIONS.md`, release notes).
- [ ] Dashboard demonstrates at least one successful resumed convergence path and one non-convergent path handled by mode policy.
