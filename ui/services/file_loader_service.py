from typing import Optional
from autonomous_delivery.ui.loader import load_artifacts


def get_file_content_at_revision(file_path: str, revision: Optional[int]) -> str:
    """
    Returns the file content for a given file_path at a specific revision.
    If revision is None, returns an empty string.
    """
    if revision is None:
        return ""
    artifacts = load_artifacts()
    # Find the artifact for the given revision and file_path
    for art in artifacts:
        if art.get("version") == revision and art.get("type", "").lower() == "codeimplementation":
            files = art.get("meta", {}).get("files", {})
            if file_path in files:
                return files[file_path]
    return ""
