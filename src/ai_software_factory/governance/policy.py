import yaml
from pathlib import Path

class PolicyManager:
    def __init__(self, policy_path: str = "config/workflow_policy.yaml"):
        self.policy_path = Path(policy_path)
        self.policy = self.load_policy()

    def load_policy(self):
        with open(self.policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

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
