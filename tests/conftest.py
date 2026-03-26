import os
import pytest

@pytest.fixture(scope="session")
def sandbox_path():
    """Fixture to provide the sandbox path for tests."""
    return os.environ.get("SANDBOX_PATH")
