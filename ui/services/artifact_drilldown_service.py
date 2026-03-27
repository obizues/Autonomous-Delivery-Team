import difflib
from typing import Dict, Any

class ArtifactDrilldownService:
    @staticmethod
    def get_patch_agent(patch: Dict[str, Any]) -> str:
        # Returns the agent/actor responsible for a patch event
        return patch.get("created_by") or patch.get("actor") or "Unknown"

    @staticmethod
    def get_patch_diff(old_content: str, new_content: str, file_name: str = "") -> str:
        # Returns a unified diff as a string
        diff = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"{file_name} (before)",
            tofile=f"{file_name} (after)",
            lineterm=""
        )
        return "\n".join(diff)

    @staticmethod
    def summarize_patch(patch: Dict[str, Any]) -> str:
        # Returns a summary string for a patch event
        status = "APPLIED" if patch["event_type"] == "PATCH_APPLIED" else "ROLLED_BACK"
        symbols = ", ".join(patch["symbols"]) if patch["symbols"] else "(none)"
        agent = ArtifactDrilldownService.get_patch_agent(patch)
        return f"- {status}: {patch['file_path']} via {patch['operation']} · symbols: {symbols} · agent: {agent}"

    @staticmethod
    def get_patch_file_contents(patch: Dict[str, Any], file_loader) -> (str, str):
        # file_loader should be a function: (file_path, revision) -> str
        file_path = patch["file_path"]
        rev_before = patch.get("revision_before")
        rev_after = patch.get("revision_after")
        old_content = file_loader(file_path, rev_before) if rev_before is not None else ""
        new_content = file_loader(file_path, rev_after) if rev_after is not None else ""
        return old_content, new_content
