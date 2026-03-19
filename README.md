# Autonomous Delivery Team

A simulation framework for an autonomous software delivery team with multi-engineer parallel orchestration, real test-driven revision loops, and governance escalation policies.

## 🎯 Overview

This system demonstrates a **fully autonomous AI-driven delivery workflow** where:
- **Multiple engineers** work in parallel via lane decomposition during implementation
- **Real test execution** drives revision cycles (pytest-based)
- **Multi-stage workflow** from backlog intake through product acceptance (11 stages)
- **Governance gates** with approval tracking and escalation policies
- **Smart termination** that escalates when progress stalls or regressions occur

## 🏗️ Architecture

### Core Components

```
autonomous_delivery/
├── src/ai_software_factory/
│   ├── workflow/          # State machine, stage orchestration, transitions
│   ├── agents/roles/      # Role-based agents (ProductOwner, Architect, Engineer, TestEngineer)
│   ├── domain/            # Data models (artifacts, enums, base classes)
│   ├── execution/         # Code patching, test running, workspace management
│   ├── governance/        # Approvals, escalations
│   ├── events/            # Event bus for audit trail
│   ├── persistence/       # In-memory stores (can be extended to DB)
│   ├── planning/          # Change planning and repo analysis
│   └── orchestration/     # Runner and engine initialization
├── ui/                    # Streamlit dashboard
└── seed_repos/            # Sample repositories (fakeUploadService, SimpleAuthService, DataPipeline)
```

### Workflow Stages (11 Total)

```
BACKLOG_INTAKE → PRODUCT_DEFINITION → REQUIREMENTS_ANALYSIS → 
ARCHITECTURE_DESIGN → IMPLEMENTATION → PULL_REQUEST_CREATED → 
ARCHITECTURE_REVIEW_GATE → PEER_CODE_REVIEW_GATE → 
TEST_VALIDATION_GATE → PRODUCT_ACCEPTANCE_GATE → DONE
```

## 🚀 Key Features

### 1. Parallel Engineer Lanes
During IMPLEMENTATION, work is decomposed into dynamic parallel lanes (1-5 based on complexity):
- Each lane gets assigned files from the change plan
- Lanes execute in isolated workspaces simultaneously
- Results are integrated back to shared sandbox
- Failures tracked per-lane

**Example Event:**
```json
{
  "event_type": "FILES_MODIFIED",
  "payload": {
    "engineer_lanes": [
      "engineer_1 files=['src/file_validator.py'] applied=2 failed=0",
      "engineer_2 files=['src/upload_service.py'] applied=1 failed=0"
    ]
  }
}
```

### 2. Real Test Execution
- Pytest runner executes actual unit tests on each iteration
- Test failures parsed to identify which tests broke
- Progress tracked: failures_reduced, no_new_failures, stable_pass_streak
- Test-driven revision loops

### 3. Escalation Policies

**Stalled Progress Escalation:**
- If no test failures reduced over 2 consecutive revisions (revision >= 2)
- Status → ESCALATED, current_stage → DONE
- Message explains: "No reduction in failing tests...requires human review"

**Regression Escalation:**
- If NEW test failures appear near revision limit (revision >= max_revisions - 1)
- Status → ESCALATED
- Message: "NEW failing tests introduced...needs human intervention"

### 4. Role-Based Agents

| Role | Stages | Behavior |
|------|--------|----------|
| **Product Owner** | Backlog, Product Definition, Product Acceptance | Deterministic approvals per repo profile |
| **Business Analyst** | Requirements Analysis | Semantic signal extraction |
| **Architect** | Architecture Design, Architecture Review | Design validation |
| **Engineer** | Implementation, PR Creation, Peer Review | Hybrid generation: LLM-first with deterministic fallback |
| **Test Engineer** | Test Validation | Test execution and failure parsing |

### 6. Optional LLM Code Generation (Safe Fallback)

- Configure LLM via environment variables for code generation during implementation
- If LLM is unavailable or generation fails, deterministic profile patches are applied
- Existing acceptance scenarios continue to run without LLM configuration

```bash
# Optional LLM configuration
set LLM_API_KEY=your_api_key_here
set LLM_API_PROVIDER=openai
set LLM_MODEL=gpt-4
```

```bash
# Anthropic example
set LLM_API_PROVIDER=anthropic
set LLM_MODEL=claude-3-opus-20240229
```

### 5. Repository Profiles
Three demo repos with scripted patch strategies:

| Profile | Files | Patch Strategy | Test Scenario |
|---------|-------|-----------------|---|
| **upload** | file_validator.py, upload_service.py | Deterministic patches per revision | Validation logic fixes |
| **auth** | auth_service.py, token_store.py | Token handling and caching | Account lockout recovery |
| **pipeline** | pipeline.py, validators.py | Data flow optimization | Regression detection |

## 📊 Dashboard

Run `streamlit run ui/app.py` to see:

- **Summary Tab**: Team overview, parallel lanes, escalation status
- **Graph Tab**: Workflow stage graph
- **Revision Insights**: Test results per revision
- **Execution Tab**: Detailed stage execution, lane assignments, artifact details
- **Work Products**: All generated artifacts (specs, PRs, test reports)
- **Event Log**: Full audit trail of all decisions and transitions

## 🧪 Acceptance Tests

```bash
python scripts/demo_acceptance.py
```

**Scenarios:**
1. **scenario_1_success**: Happy path - all gates approve, tests pass
2. **scenario_2_semantic_signals**: Semantic planning signals integrated
3. **scenario_3_auth_success**: Auth profile with escalation on stall
4. **scenario_4_pipeline_success**: Pipeline profile with regression handling

**Expected Output:**
```
scenario_1_success: status=COMPLETED revision=2 events=79
scenario_2_semantic_signals: status=COMPLETED revision=2 events=79
scenario_3_auth_success: status=COMPLETED revision=2 events=77
scenario_4_pipeline_success: status=COMPLETED revision=2 events=77
acceptance: PASSED
```

## 🔧 Running the System

### Quick Start
```bash
# Set up Python environment
python -m venv .venv
source .venv/Scripts/activate  # Windows
source .venv/bin/activate       # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run acceptance tests
python scripts/demo_acceptance.py

# Launch dashboard
streamlit run ui/app.py
```

### Optional: Enable SQLite Persistence
```bash
# Default behavior is in-memory persistence
# Enable SQLite-backed state/artifact persistence for runs:
set ASF_PERSISTENCE_BACKEND=sqlite   # Windows PowerShell: $env:ASF_PERSISTENCE_BACKEND='sqlite'
set ASF_SQLITE_PATH=generated_workspace/asf_state.db

# Then run as usual
python scripts/demo_acceptance.py
```

### Run Single Workflow
```python
from src.ai_software_factory.orchestration.runner import run_demo_workflow

result = run_demo_workflow("fake_upload_service")
print(f"Status: {result['status']}")
print(f"Revisions: {result['revision']}")
print(f"Events: {result['event_count']}")
```

## 📈 Execution Flow Example

```
Workflow Start (backlog: "Add file validation")
  ↓
BACKLOG_INTAKE (ProductOwner) → artifacts created
  ↓
PRODUCT_DEFINITION (ProductOwner) → product spec created
  ↓
REQUIREMENTS_ANALYSIS (BA) → requirements spec created
  ↓
ARCHITECTURE_DESIGN (Architect) → architecture spec created
  ↓
IMPLEMENTATION (Engineer) 
  ├─ Lane 1: src/file_validator.py (isolated workspace)
  ├─ Lane 2: src/upload_service.py (isolated workspace)
  └─ Lane 3: (empty or other files)
  Results integrated → PR created
  ↓
PULL_REQUEST_CREATED (Engineer) → pull request artifact
  ↓
ARCHITECTURE_REVIEW_GATE (Architect)
  ├─ Decision: APPROVED → continue
  └─ Decision: REQUEST_CHANGES → revision += 1, back to IMPLEMENTATION
  ↓
PEER_CODE_REVIEW_GATE (Engineer)
  ├─ Decision: APPROVED → continue
  └─ Decision: REQUEST_CHANGES → revision += 1, back to IMPLEMENTATION
  ↓
TEST_VALIDATION_GATE (TestEngineer)
  ├─ Tests PASS → continue
  ├─ Tests FAIL & fixable → REQUEST_CHANGES, back to IMPLEMENTATION
  └─ Tests FAIL & stalled 2 revisions → ESCALATE to human
  ↓
PRODUCT_ACCEPTANCE_GATE (ProductOwner) → APPROVED
  ↓
DONE (all artifacts, final_status=COMPLETED)
```

## 🎓 Key Design Decisions

1. **Lane-based parallelism during IMPLEMENTATION**: Scales easily, avoids full engine redesign
2. **Deterministic agent behavior**: Seeded patches + test results → reproducible workflows
3. **Event-driven audit trail**: Every decision, artifact, and transition logged
4. **Escalation on stall, not max revisions**: Fails fast when progress stops, not after N attempts
5. **In-memory persistence**: Fast POC; can extend to database

## 🚦 Future Enhancements

### Short-term
- [ ] Real repository integration: Clone actual repos, run real patch logic
- [ ] Human-in-the-loop escalation handling: Accept feedback and resume workflow

### Medium-term
- [ ] True parallel agent tracks: Each engineer independently progresses through pipeline
- [ ] Extend LLM usage to additional agents (Architect/BA/ProductOwner)
- [ ] Persistent storage hardening: indexes, replay tooling, and migration strategy

### Long-term
- [ ] Distributed execution: Multiple machines running engineer lanes
- [ ] Policy-driven governance and compliance checks
- [ ] Multi-tenant orchestration and workspace isolation

## 📝 License

MIT (or your preferred license)

## 👥 Contributing

Contributions welcome! See development guidelines in CONTRIBUTING.md

---

**Built for**: AI-driven autonomous delivery team orchestration  
**Status**: POC - Production-ready core engine with demo repos  
**Last Updated**: March 2026
