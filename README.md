# Autonomous Software Delivery System (POC4)

A Python scaffold for simulating an AI-native Agile software delivery organization with role-based agents, review gates, PR loops, testing, and persistent workflow state.

## Proposed Project Structure

```text
Autonomous Software Delivery System/
├─ pyproject.toml
├─ README.md
├─ main.py
├─ src/
│  └─ autonomous_delivery/
│     ├─ __init__.py
│     ├─ demo.py
│     ├─ agents/
│     │  ├─ __init__.py
│     │  ├─ base.py
│     │  ├─ roles.py
│     │  └─ mock_agents.py
│     ├─ models/
│     │  ├─ __init__.py
│     │  └─ artifacts.py
│     └─ workflow/
│        ├─ __init__.py
│        ├─ stages.py
│        ├─ events.py
│        ├─ state.py
│        ├─ persistence.py
│        └─ engine.py
└─ tests/
   └─ test_workflow_engine.py
```

## Core Workflow Engine

The workflow engine orchestrates stages in this sequence:

1. Product Owner definition
2. Business Analyst requirements expansion
3. Architect system design
4. Engineers implementation
5. Pull Request creation
6. Architecture review gate
7. Peer code review gate
8. Test execution gate
9. Revision cycle when gate fails
10. Product Owner final acceptance

### Key properties

- Structured artifacts are produced at each stage.
- Review/test rejections trigger revision cycles.
- All actions emit events for logging/audit.
- Workflow state is persisted after each stage.
- Agents interact through a shared orchestration layer (`WorkflowEngine`).

## Run

```bash
python main.py
```

## Test

```bash
pytest
```
