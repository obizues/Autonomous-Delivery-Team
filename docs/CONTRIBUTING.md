# Contributing

## Development Flow

1. Create a focused branch.
2. Make minimal, scoped changes.
3. Run acceptance checks.
4. Update docs if behavior/UI changes.
5. Open PR with clear before/after summary.

## Local Validation

```powershell
$env:PYTHONPATH='src'
python scripts/demo_acceptance.py
.venv\Scripts\python.exe ui/launcher.py --ui-only
```

## Coding Guidelines

- Keep stage logic in engine/role files, not UI files.
- Preserve event/audit emissions when modifying workflow behavior.
- Prefer deterministic fallbacks when adding optional LLM behavior.
- Keep UI labels consistent with domain terms (Engineer Agents, Parallel Lanes).

## Documentation Requirements

Changes should include docs updates when they alter:
- stage sequence,
- gate behavior,
- artifact semantics,
- dashboard terminology.

Before opening a PR, check the requirements mapping in `docs/OPERATIONS.md` under **Requirements Traceability** and ensure your change preserves or updates its verification path.

Minimum verification for workflow-affecting changes:

```powershell
$env:PYTHONPATH='src'
python scripts/demo_acceptance.py
python scripts/demo_resume_e2e.py
```
