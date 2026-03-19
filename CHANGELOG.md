# Changelog

All notable changes to this project are documented in this file.

## [v0.2.0] - 2026-03-19

### Added
- Escalation decision capture on `HumanIntervention` artifacts:
  - selected response template,
  - human guidance,
  - resume stage,
  - responder identity,
  - resume max steps metadata.
- Escalation Decision cards across dashboard surfaces (Overview, Process, Execution, Final Outcome).
- Revision budget exhaustion escalation guard to prevent indefinite review loops.

### Changed
- Resume control model now supports rejection-based budget semantics (`ASF_RESUME_MAX_REJECTIONS`) with step-budget conversion.
- Peer code review gate hardened with weighted scoring and stricter revision-aware thresholds.
- Architecture review gate hardened with implementation-to-architecture alignment checks.
- Final outcome / DONE status views now include escalation reason context.

### Fixed
- Dashboard resume path now resolves the correct SQLite state store by workflow ID.
- Engineer team overview now resolves Engineer Team labels consistently for latest-stage display.
- Acceptance and resume E2E flows validated after gate hardening.

## [v0.1.0] - 2026-03-18

### Added
- Initial release packaging and documentation for public viewing.
- Parallel engineer orchestration with explicit story-slice assignments.
- Deterministic cross-review matrix for lane-to-lane peer review.
- Merge Conflict Gate stage in workflow sequence.
- Engineer-focused dashboard control tower and lane insights.
- Human escalation + resume flow persisted through artifacts/events.
- Release support docs under `docs/`.

### Changed
- Refactored dashboard monolith into focused modules:
  - `ui/config.py`
  - `ui/loader.py`
  - `ui/query.py`
  - `ui/analytics.py`
  - `ui/actions.py`
  - lean `ui/app.py`
- Standardized terminology to **Engineer Agents** and **Parallel Lanes**.
- Improved reviewer attribution in review artifacts to use explicit cross-review pairs.
- Enhanced final outcome checklist rendering with decision-aware visual markers.

### Fixed
- Final outcome no longer dumps full markdown artifact; now shows concise status + checklist.
- Launcher no longer opens duplicate browser windows.
- Timeline lane heading HTML rendering issue.
- Review artifact identity labeling now favors reviewer role/persona where applicable.

### Notes
- This release is tagged by repository version marker `VERSION` as `v0.1.0`.
- Next planned milestones are listed in `docs/ROADMAP.md`.
