
"""
Agent/Role Customization and Configuration System

This module allows you to define custom behaviors, preferences, and collaboration patterns for each agent and role.

- You can specify agent parameters (e.g., expertise, style, strictness, collaboration mode)
- You can override or extend default agent logic per role or per agent instance
- You can define which agents collaborate on which stages, and how their outputs are merged

Example config structure:

AGENT_CONFIG = {
    "engineer": {
        "collaboration_mode": "pair_programming",
        "preferred_partners": ["test_engineer", "architect"],
        "strictness": "high",
        "review_style": "detailed",
    },
    "test_engineer": {
        "collaboration_mode": "tdd",
        "preferred_partners": ["engineer"],
        "test_coverage_goal": 0.95,
    },
    "product_owner": {
        "collaboration_mode": "requirements_clarification",
        "acceptance_criteria_format": "Gherkin",
    },
    # Add more roles/agents as needed
}

# You can import and use AGENT_CONFIG in the workflow engine or agent classes to customize behavior.

"""

AGENT_CONFIG = {
    "engineer": {
        "collaboration_mode": "pair_programming",
        "preferred_partners": ["test_engineer", "architect"],
        "strictness": "high",
        "review_style": "detailed",
    },
    "test_engineer": {
        "collaboration_mode": "tdd",
        "preferred_partners": ["engineer"],
        "test_coverage_goal": 0.95,
    },
    "product_owner": {
        "collaboration_mode": "requirements_clarification",
        "acceptance_criteria_format": "Gherkin",
    },
    "business_analyst": {
        "collaboration_mode": "joint_analysis",
        "preferred_partners": ["product_owner"],
    },
    "architect": {
        "collaboration_mode": "design_review",
        "preferred_partners": ["engineer"],
    },
}
