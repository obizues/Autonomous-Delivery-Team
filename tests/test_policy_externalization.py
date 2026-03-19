import pytest
import os
import tempfile
from ai_software_factory.governance.policy import PolicyManager


def test_policy_externalization_loading():
    with tempfile.TemporaryDirectory() as tmpdir:
        policy_path = os.path.join(tmpdir, "policy.json")
        with open(policy_path, "w") as f:
            f.write('{"revision_limit": 3, "gate_rules": {"ARCHITECTURE_REVIEW_GATE": "strict"}}')
        manager = PolicyManager()
        manager.load(policy_path)
        assert manager.get("revision_limit") == 3
        assert manager.get("gate_rules")["ARCHITECTURE_REVIEW_GATE"] == "strict"


def test_policy_externalization_adaptation():
    manager = PolicyManager()
    manager.set("revision_limit", 5)
    assert manager.get("revision_limit") == 5
    manager.set("gate_rules", {"PEER_CODE_REVIEW_GATE": "lenient"})
    assert manager.get("gate_rules")["PEER_CODE_REVIEW_GATE"] == "lenient"

