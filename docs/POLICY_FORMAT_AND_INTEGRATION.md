# Workflow Policy Format and Integration

## Policy File Location
- `config/workflow_policy.yaml`

## Format (YAML)
```
version: v0.3.1
policy_id: default
revision_budget: 5
rejection_runway: 3
escalation_triggers:
  - gate_failure
  - revision_exhaustion
  - operator_request
stages:
  BACKLOG_INTAKE:
    gate_policy:
      min_artifacts: 1
      allow_empty: false
  ...
escalation_modes:
  abandon:
    terminal: true
    rationale: "Explicit non-recoverable status and reason taxonomy."
  best_effort:
    terminal: false
    rationale: "Constrained deliverable package without full acceptance."
policy_versioning:
  enabled: true
  snapshot_on_run: true
validation:
  fail_fast: true
  schema_check: true
```

## Integration
- PolicyManager loads and validates YAML config.
- WorkflowEngine uses PolicyManager for revision budget, gate policies, escalation triggers, and modes.
- Gate policies (e.g., min_artifacts) are enforced per stage.
- Revision budget is checked before advancing workflow.

## Extending Policy
- Add new fields to YAML as needed (e.g., custom gates, operator modes).
- Update PolicyManager accessors for new fields.

## Example Usage
```python
from ai_software_factory.governance.policy import PolicyManager
policy = PolicyManager()
print(policy.get_revision_budget())
print(policy.get_gate_policy("IMPLEMENTATION"))
```

## Next Steps
- Integrate policy-driven adaptation for more workflow decisions.
- Document policy versioning and audit trail.
