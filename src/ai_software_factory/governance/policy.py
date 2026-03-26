import yaml
from pathlib import Path

class PolicyManager:
    def __init__(self, policy_path: str | None = None):
        # Always resolve policy path relative to project root
        if policy_path is None:
            # Find project root (directory containing this file, up 3 levels)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.policy_path = project_root / "config" / "workflow_policy.yaml"
        else:
            self.policy_path = Path(policy_path).resolve()
        self.policy = self.load_policy()

    def load_policy(self):
        with open(self.policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load(self, policy_path):
        self.policy_path = Path(policy_path)
        self.policy = self.load_policy()
        return self.policy

    def set(self, key, value):
        self.policy[key] = value
        return self.policy

    def get(self, key):
        return self.policy.get(key)

    def get_gate_policy(self, stage: str):
        return self.policy.get("stages", {}).get(stage, {}).get("gate_policy", {})

    def get_revision_budget(self):
        return self.policy.get("revision_budget", 5)

    def get_escalation_triggers(self):
        return self.policy.get("escalation_triggers", [])

    def get_escalation_modes(self):
        return self.policy.get("escalation_modes", {})

    def get_policy_version(self):
        return self.policy.get("version", "unknown")

    def validate(self):
        # Basic schema check
        assert "stages" in self.policy, "Policy missing stages section"
        assert "revision_budget" in self.policy, "Policy missing revision_budget"
        return True

class GatePolicyEvaluator:
    def __init__(self, policy_manager):
        self.policy_manager = policy_manager

    def get_gate_policy(self, stage):
        return self.policy_manager.get_gate_policy(stage)

    def get_revision_budget(self):
        return self.policy_manager.get_revision_budget()
