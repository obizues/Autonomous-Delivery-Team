# Getting Started

Welcome to the Autonomous Delivery System! This project is hosted at [obizues/Autonomous-Delivery-Team](https://github.com/obizues/Autonomous-Delivery-Team) on the `main` branch.

## Prerequisites

- Python 3.11+
- Windows PowerShell (commands below use PowerShell syntax)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Set source path for local module imports:

```powershell
$env:PYTHONPATH='src'
```

## Run Acceptance Scenarios

```powershell
python scripts/demo_acceptance.py
```

Expected final line:

```text
acceptance: PASSED
```

## Run Dashboard Launcher

```powershell
.venv\Scripts\python.exe ui/launcher.py
```

## References
- Repository: [obizues/Autonomous-Delivery-Team](https://github.com/obizues/Autonomous-Delivery-Team)
- Branch: main
- Owner: obizues
- `--ui-only`
- `--escalation-demo`
- `--port 8600`
- `--seed-repo simple_auth_service`

## Run Engine Directly

```powershell
python -m ai_software_factory
```

## Optional: SQLite Persistence

```powershell
$env:ASF_PERSISTENCE_BACKEND='sqlite'
$env:ASF_SQLITE_PATH='generated_workspace/asf_state_ui.db'
```

## Optional: Real Git Repository Input

```powershell
$env:ASF_REPO_URL='https://github.com/owner/repo.git'
$env:ASF_REPO_REF='main'
python -m ai_software_factory
```

## Optional: Resume Escalated Workflow

```powershell
$env:ASF_PERSISTENCE_BACKEND='sqlite'
$env:ASF_SQLITE_PATH='generated_workspace/asf_state_ui.db'
$env:ASF_RESUME_WORKFLOW_ID='<workflow_id>'
$env:ASF_HUMAN_RESPONSE='Resume with minimal safe fixes first.'
$env:ASF_HUMAN_RESPONSE_TEMPLATE='Retry with safer fix strategy'
$env:ASF_RESUME_STAGE='IMPLEMENTATION'
$env:ASF_RESUME_RESPONDER='human_operator'
$env:ASF_RESUME_MAX_REJECTIONS='3'
python -m ai_software_factory
```

`ASF_RESUME_MAX_STEPS` remains supported for backward compatibility, but `ASF_RESUME_MAX_REJECTIONS` is recommended.

## End-to-End Resume Validation

```powershell
python scripts/demo_resume_e2e.py
```
