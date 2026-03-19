import pytest
from ai_software_factory.agents.base import Agent, AgentContext

class TestAgent(Agent):
    def act(self, context):
        class Result:
            produced_artifacts = ["artifact1"]
            escalation_request = None
            decision = "APPROVED"
            notes = "Test note"
        return Result()


def test_agent_act_returns_expected_result():
    context = AgentContext(workflow_state=None, artifacts=[])
    agent = TestAgent()
    result = agent.act(context)
    assert hasattr(result, "produced_artifacts")
    assert hasattr(result, "decision")
    assert result.decision == "APPROVED"

