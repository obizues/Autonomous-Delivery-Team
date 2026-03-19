# Release Notes — v0.1.0

Release date: 2026-03-18

## Highlights

- Multi-agent autonomous software delivery simulation end-to-end.
- Parallel engineer agents with lane decomposition and story-slice ownership.
- Cross-review matrix and merge conflict gate integrated into workflow.
- Escalation and human-guided resume support.
- Refactored and upgraded Streamlit dashboard with role/gate clarity.

## Included Workflow Features

- Stage orchestration across backlog, design, implementation, reviews, testing, and acceptance.
- Revision loops driven by gate decisions.
- Event and artifact persistence with dashboard replayability.

## Dashboard UX Improvements Included

- Engineer Control Tower with lane and cross-review visibility.
- Explicit reviewer attribution in review artifacts.
- Terminology standardized to Engineer Agents and Parallel Lanes.
- Improved final outcome criteria visualization.

## Compatibility Notes

- Existing demo workflows remain supported.
- Optional LLM integrations still degrade gracefully to deterministic behavior.

## Upgrade Notes

- Install dependencies using `requirements.txt`.
- If using SQLite persistence, keep `ASF_SQLITE_PATH` stable across resume workflows.
