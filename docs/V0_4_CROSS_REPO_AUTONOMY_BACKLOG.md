# v0.4 Cross-Repo Autonomy Backlog

## Goal

Enable the system to safely ingest, reason about, modify, validate, and deliver changes across arbitrary repositories (not only seeded demo profiles) with predictable quality and controlled risk.

## v0.4 Exit Criteria

- At least 3 previously unseen repos (different stacks) pass end-to-end autonomous change runs.
- System can auto-detect repo profile, execution strategy, and validation commands without hard-coded seed assumptions.
- Patch attempts are bounded by safety policy (churn limits, protected paths, rollback, escalation modes).
- PR-ready outputs include explainable rationale, risk summary, and reproducible run metadata.
- Deterministic replay is possible from persisted policy + run snapshot + event stream.

## Phase 1 — Universal Repo Ingestion (MVP)

- [ ] Add repo profiler for language/framework/build/test detection.
  - Detect: package managers, test runners, linters, type-checkers, monorepo markers.
- [ ] Add workspace bootstrap matrix.
  - Python/Node first; define pluggable adapters for additional ecosystems.
- [ ] Add capability report artifact.
  - Persist detected commands, confidence, unsupported gaps, fallback plan.
- [ ] Add unsupported-repo safe fail path.
  - Escalate with explicit reason taxonomy rather than partial unsafe execution.

## Phase 2 — Generalized Change Planning

- [ ] Add stack-agnostic target selection pipeline.
  - Inputs: failing logs, semantic search, import graph, symbol map.
- [ ] Add confidence-scored edit plan.
  - File/symbol candidates, expected impact, rollback strategy.
- [ ] Add bounded edit policy.
  - Max files, max diff size, protected directories, generated-file handling.
- [ ] Add plan quality checks before patch execution.
  - Reject low-confidence broad edits; force escalation or narrower retry.

## Phase 3 — Validation and Delivery Reliability

- [ ] Add validation orchestration tiers.
  - Tier 1 targeted checks, Tier 2 full tests, Tier 3 lint/type/build gates.
- [ ] Add flaky-test handling policy.
  - Retry window + confidence downgrade + non-determinism tagging.
- [ ] Add git delivery automation.
  - Branching, atomic commits, PR generation payload, CI polling.
- [ ] Add merge-conflict handling for non-linear histories.
  - Rebase/retry policy with bounded attempts.

## Phase 4 — Safety, Governance, and Explainability

- [ ] Add security/compliance guardrails.
  - Secret scanning, license checks, restricted-path policies.
- [ ] Add per-run policy snapshot + signed provenance metadata.
  - Persist effective policy, tool versions, command outputs, artifact hashes.
- [ ] Add explainability bundle artifact.
  - Why changed, what changed, risk before/after, unresolved concerns.
- [ ] Add human approval checkpoints by risk class.
  - Auto-approve low risk, mandatory approval for medium/high risk.

## Phase 5 — Learning and Convergence

- [ ] Add repo memory store.
  - Capture prior failing signatures, successful remediation patterns.
- [ ] Add convergence scoring.
  - Re-escalation rate, retries-to-success, false-progress detection.
- [ ] Add adaptive policy tuning suggestions.
  - Recommend threshold/policy changes based on run history.
- [ ] Add cross-repo benchmark harness.
  - Compare autonomy quality across repo archetypes.

## Reference Repo Matrix (Minimum)

- [ ] Python service repo (pytest + static checks)
- [ ] Node/TypeScript API repo (npm/pnpm + test/lint)
- [ ] Monorepo with multiple packages/apps

## Definition of Done

- [ ] All phase exit checks pass.
- [ ] Cross-repo benchmark harness reports reproducible success on baseline matrix.
- [ ] Dashboard surfaces autonomy scorecard, risk class, and policy snapshot for each run.
- [ ] Operations runbook includes incident handling for unsupported repos, flaky validation, and high-risk patches.
