"""
UI configuration: stage ordering, metadata, labels, theme tokens.
No Streamlit imports — safe to import anywhere.
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DEMO_OUTPUT = BASE_DIR / "demo_output" / "latest"
UI_SQLITE_PATH = "generated_workspace/asf_state_ui.db"

STAGE_ORDER = [
    "BACKLOG_INTAKE",
    "PRODUCT_DEFINITION",
    "REQUIREMENTS_ANALYSIS",
    "ARCHITECTURE_DESIGN",
    "IMPLEMENTATION",
    "PULL_REQUEST_CREATED",
    "MERGE_CONFLICT_GATE",
    "ARCHITECTURE_REVIEW_GATE",
    "PEER_CODE_REVIEW_GATE",
    "TEST_VALIDATION_GATE",
    "PRODUCT_ACCEPTANCE_GATE",
    "DONE",
]

STAGE_META: dict[str, tuple[str, str, str]] = {
    "BACKLOG_INTAKE":           ("📋", "Backlog Intake",          "Product Owner"),
    "PRODUCT_DEFINITION":       ("📝", "Product Definition",       "Product Owner"),
    "REQUIREMENTS_ANALYSIS":    ("🔍", "Requirements Analysis",    "Business Analyst"),
    "ARCHITECTURE_DESIGN":      ("🏗️", "Architecture Design",      "Architect"),
    "IMPLEMENTATION":           ("💻", "Implementation",           "Engineer"),
    "PULL_REQUEST_CREATED":     ("🔀", "Pull Request",             "Engineer"),
    "MERGE_CONFLICT_GATE":      ("🧷", "Merge Conflict Gate",      "Merge Conflict Guard"),
    "ARCHITECTURE_REVIEW_GATE": ("🏛️", "Architecture Review",     "Architect"),
    "PEER_CODE_REVIEW_GATE":    ("👥", "Peer Code Review",         "Engineer"),
    "TEST_VALIDATION_GATE":     ("🧪", "Test Validation",          "Test Engineer"),
    "PRODUCT_ACCEPTANCE_GATE":  ("✅", "Product Acceptance",        "Product Owner"),
    "DONE":                     ("🎉", "Done",                     "—"),
}

REVIEW_GATES = {
    "MERGE_CONFLICT_GATE",
    "ARCHITECTURE_REVIEW_GATE",
    "PEER_CODE_REVIEW_GATE",
    "TEST_VALIDATION_GATE",
    "PRODUCT_ACCEPTANCE_GATE",
}

ARTIFACT_TYPE_LABELS = {
    "BacklogItem":        "Backlog Item",
    "RequirementsSpec":   "Requirements Spec",
    "ArchitectureSpec":   "Architecture Design",
    "CodeImplementation": "Implementation Plan",
    "EscalationArtifact": "Workflow Escalation",
    "HumanIntervention":  "Human Intervention",
    "PullRequest":        "Pull Request",
    "ReviewFeedback":     "Review Feedback",
    "TestResult":         "Test Report",
}

EVENT_ICONS = {
    "WORKFLOW_STARTED":          "🚀",
    "STAGE_STARTED":             "▶️",
    "STAGE_COMPLETED":           "✅",
    "ARTIFACT_CREATED":          "📄",
    "DECISION_MADE":             "⚖️",
    "TRANSITION_OCCURRED":       "➡️",
    "APPROVAL_RECORDED":         "✔️",
    "ESCALATION_RAISED":         "⚠️",
    "REVISION_STARTED":          "🔄",
    "REPO_SCANNED":              "🗂️",
    "CHANGE_PLAN_GENERATED":     "🧭",
    "FILES_MODIFIED":            "🛠️",
    "PATCH_APPLIED":             "🧩",
    "PATCH_ROLLED_BACK":         "↩️",
    "TEST_EXECUTION_STARTED":    "🧪",
    "TEST_EXECUTION_COMPLETED":  "📋",
    "TEST_PASSED":               "✅",
    "TEST_FAILED":               "❌",
    "HUMAN_FEEDBACK_RECORDED":   "🧑‍💼",
    "ESCALATION_RESOLVED":       "🟢",
    "WORKFLOW_RESUMED":          "🔁",
    "WORKFLOW_COMPLETED":        "🏁",
}

# ── Theme tokens ─────────────────────────────────────────────────────────────

TOKENS: dict[str, str] = {
    "app_bg":         "#f3f6fb",
    "sidebar_bg":     "#ffffff",
    "text_primary":   "#0b1220",
    "text_secondary": "#1f2937",
    "text_muted":     "#334155",
    "code_fg":        "#1e40af",
    "code_bg":        "#e0ecff",
    "surface":        "#ffffff",
    "surface_alt":    "#f1f5f9",
    "border":         "#94a3b8",
    "hover":          "#dbe7f5",
    "chip_bg":        "#ffffff",
    "wf_current_bg":  "#dbeafe",
    "wf_loop_bg":     "#fff7ed",
}
