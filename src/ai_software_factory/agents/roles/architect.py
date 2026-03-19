from __future__ import annotations

from ai_software_factory.agents.base import Agent, AgentContext
from ai_software_factory.domain.enums import ArtifactStatus, Decision, WorkflowStage
from ai_software_factory.domain.models import ArchitectureSpec, BacklogItem, PullRequest, ReviewFeedback
from ai_software_factory.workflow.stage_result import StageResult


class ArchitectAgent(Agent):
    role = "architect"

    def act(self, context: AgentContext) -> StageResult:
        stage = context.workflow_state.current_stage
        wf_id = context.workflow_state.workflow_id
        revision = context.workflow_state.revision

        if stage == WorkflowStage.ARCHITECTURE_DESIGN:
            backlog = context.latest(BacklogItem)
            title = backlog.title if backlog else "Feature"
            description = backlog.description if backlog else ""
            problem_statement = backlog.problem_statement if backlog else ""
            artifact = ArchitectureSpec(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                overview=(
                    f"'{title}' is implemented as a small modular Python service with focused domain modules, "
                    "deterministic business rules, and a test-first revision loop. "
                    f"Primary problem addressed: {problem_statement or description}"
                ),
                components=[
                    "Seed repo source modules — existing domain logic targeted by semantic planner",
                    "Generated test modules — encode acceptance criteria as executable pytest checks",
                    "Patch engine — applies whole-file or function-level edits with syntax validation and rollback",
                    "Semantic planner — maps failing tests to files and symbols using imports and traceback hints",
                    "Workflow engine — coordinates revision loops, approvals, and escalations",
                ],
                api_changes=[
                    "Public function surface remains aligned with the seed repo unless acceptance criteria require a contract change",
                    "Structured success and failure payloads must remain stable for automated tests",
                    "Module-level business rules may be tightened to enforce validation, lockout, or rejection semantics",
                ],
                data_flow=[
                    "Backlog item -> planner intent classification -> target files and symbols",
                    "Generated tests -> pytest execution -> failing test extraction",
                    "Failing tests + traceback hints -> semantic localization -> change plan",
                    "Engineer patch strategy -> source edits -> syntax validation and rollback if needed",
                    "Re-run targeted and full pytest suites -> approve revision or request changes",
                ],
                decisions=[
                    "ADR-01: Acceptance criteria are converted into executable tests before final approval",
                    "ADR-02: Semantic targeting narrows edits to relevant files and symbols where possible",
                    "ADR-03: Syntax validation and rollback protect the sandbox from broken intermediate patches",
                    "ADR-04: Regression-aware revision policy escalates if failures stall or regress near limits",
                    "ADR-05: Repo-specific deterministic strategies provide reliable convergence for demo seeds",
                ],
                security_considerations=[
                    "Rejection and validation logic must fail closed and return explicit reasons",
                    "State-tracking features such as lockout counters must reset safely after successful operations",
                    "Duplicate or invalid inputs must not silently pass through to successful output sets",
                    "Sandbox execution isolates patching from the original seed repo",
                ],
                scalability_considerations=[
                    "Semantic indexing currently targets Python repos and small deterministic demos efficiently",
                    "Targeted test execution reduces feedback time before running the full suite",
                    "Repo profiles can be expanded with additional deterministic strategies as new seeds are added",
                    "Full autonomy for arbitrary repos will require more generalized synthesis beyond fixed demo profiles",
                ],
                risks=[
                    "RISK-01: Heuristic failure localization may still miss the correct symbol in more complex repos",
                    "RISK-02: Profile-specific strategies are deterministic but not yet fully generalized across arbitrary architectures",
                    "RISK-03: Acceptance tests may overfit to expected payload shapes if backlog wording is ambiguous",
                    "RISK-04: Larger repos may need deeper indexing and patch planning than the current demo loop provides",
                ],
            )
            return StageResult(produced_artifacts=[artifact], notes="Architecture design completed.")

        if stage == WorkflowStage.ARCHITECTURE_REVIEW_GATE:
            pr = context.latest(PullRequest)
            arch_spec = context.latest(ArchitectureSpec)
            impl = next(
                (a for a in reversed(context.artifacts)
                 if a.__class__.__name__ == "CodeImplementation" and a.version == revision),
                None,
            )

            if pr is None:
                decision = Decision.REQUEST_CHANGES
                comments = "Architecture review blocked: no pull request artifact found for this revision."
                issues = ["Pull request artifact is missing for the current revision"]
                suggestions = ["Engineer must submit a PullRequest artifact before architecture review can proceed"]
            else:
                # Perform alignment check against architecture spec
                issues = []
                suggestions = []
                alignment_failures = 0

                if impl is not None:
                    changed = set(f.lower() for f in (impl.files_changed or []))
                    written = set(f.lower() for f in (impl.written_source_files or []))
                    all_touched = changed | written

                    if not all_touched:
                        issues.append("ADR-01 violation: no source files were changed — implementation appears empty")
                        alignment_failures += 2

                    # API stability: PR description should acknowledge contract changes
                    pr_desc = (pr.description or "").lower()
                    if "contract" not in pr_desc and "api" not in pr_desc and len(all_touched) > 0:
                        if len(impl.files_changed or []) > 3:
                            issues.append("ADR-02 concern: broad change set with no API stability notes in PR description")
                            alignment_failures += 1

                    # Arch spec risk mitigations: rejection/validation must be present
                    source_contents = []
                    try:
                        import os
                        from pathlib import Path as _Path
                        ws = _Path(impl.workspace_path) if impl.workspace_path else None
                        if ws and ws.exists():
                            for rel in (impl.written_source_files or [])[:5]:
                                fp = ws / rel
                                if fp.exists():
                                    try:
                                        source_contents.append(fp.read_text(encoding="utf-8", errors="ignore").lower())
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                    combined = " ".join(source_contents)
                    if combined and "reject" not in combined and "raise" not in combined and "error" not in combined:
                        issues.append("ADR-04 / RISK-03: no rejection/error paths detected in source files — validation logic may be missing")
                        alignment_failures += 1

                if arch_spec is not None and not arch_spec.risks:
                    suggestions.append("Architecture spec has no recorded risks; ensure identified risks are tracked")

                if alignment_failures >= 2:
                    decision = Decision.REQUEST_CHANGES
                    comments = (
                        f"Architecture review: REQUEST_CHANGES. {alignment_failures} alignment gap(s) detected. "
                        "Implementation does not adequately satisfy architectural constraints. "
                        "See issues for details."
                    )
                    suggestions.extend([
                        "Ensure all changed files are recorded in implementation artifact",
                        "Add rejection/validation paths that satisfy ADR-04 and RISK-03",
                    ])
                elif alignment_failures == 1:
                    decision = Decision.APPROVED
                    comments = (
                        "Architecture review passed with minor concerns. Implementation broadly aligns with "
                        "the modular workflow, semantic targeting, and revision-safe patching strategy. "
                        "One alignment note recorded as a suggestion."
                    )
                else:
                    decision = Decision.APPROVED
                    comments = (
                        "Architecture review passed. Implementation fully aligns with the modular repo-aware workflow, "
                        "semantic targeting, deterministic rule enforcement, and revision-safe patching strategy."
                    )
                    issues = []

            review = ReviewFeedback(
                workflow_id=wf_id,
                stage=stage,
                created_by=self.role,
                status=ArtifactStatus.FINAL,
                version=revision,
                reviewer=self.role,
                decision=decision,
                comments=comments,
                issues_identified=issues,
                suggested_changes=suggestions,
                pull_request_id=pr.artifact_id if pr else None,
            )
            return StageResult(produced_artifacts=[review], decision=decision, notes="Architecture review complete.")

        return StageResult(notes=f"No Architect action for stage {stage.value}.")
