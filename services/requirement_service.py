"""
requirement_service.py

Service for handling new business requirements and triggering the workflow engine pipeline.
"""

from typing import Optional
from ai_software_factory.orchestration.runner import create_workflow_engine
from ai_software_factory.domain.models import RequirementsSpec

def process_requirement(requirement: str) -> Optional[str]:
    """
    Process a new business requirement by triggering the workflow engine pipeline.
    Returns a status message or None.
    """
    print(f"[process_requirement] Received requirement: {requirement}")
    # Instantiate the workflow engine using the factory
    engine = create_workflow_engine()
    # Create a requirements artifact/backlog item
    backlog_item = RequirementsSpec(summary=requirement)
    # Start the workflow
    state = engine.start(backlog_item)
    # Optionally, run the workflow to completion
    engine.run_until_terminal(state.workflow_id)
    return f"Requirement processed and workflow started: {state.workflow_id}"
