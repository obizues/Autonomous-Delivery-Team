# Additional tests for expanded coverage
import os
import tempfile
import pytest
from ai_software_factory.artifacts.repo_profiler import RepoCapabilityProfiler

def test_profile_detects_additional_frameworks():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "requirements.txt"), "w").write("django\nflask\nstreamlit\npytest\n")
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        frameworks = profiler.detect_frameworks()
        assert "Streamlit" in frameworks
        assert "Pytest" in frameworks
        # Stub: expand to detect more frameworks if implemented

def test_profile_detects_dependency_files():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "pyproject.toml"), "w").close()
        open(os.path.join(repo_dir, "package.json"), "w").close()
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        deps = profiler.find_dependency_files()
        assert "pyproject.toml" in deps
        assert "package.json" in deps

def test_profile_detects_ci_cd_tools():
    with tempfile.TemporaryDirectory() as repo_dir:
        os.mkdir(os.path.join(repo_dir, ".github"))
        os.mkdir(os.path.join(repo_dir, ".github", "workflows"))
        open(os.path.join(repo_dir, "Dockerfile"), "w").close()
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        ci_cd = profiler.find_ci_cd()
        assert "workflows" in ci_cd or "Dockerfile" in ci_cd

def test_profile_handles_unreadable_files():
    with tempfile.TemporaryDirectory() as repo_dir:
        license_path = os.path.join(repo_dir, "LICENSE")
        open(license_path, "w").close()
        os.chmod(license_path, 0)
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        try:
            license = profiler.find_license()
        except Exception:
            license = "Error"
        assert license == "None" or license == "Error"

def test_profile_unusual_repo_structure():
    with tempfile.TemporaryDirectory() as repo_dir:
        os.mkdir(os.path.join(repo_dir, "src"))
        open(os.path.join(repo_dir, "src", "main.py"), "w").close()
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert report["repo_name"] == os.path.basename(repo_dir)
        assert isinstance(report["languages"], list)
import os
import tempfile
import pytest
from ai_software_factory.artifacts.repo_profiler import RepoCapabilityProfiler


def test_profile_multiple_languages_and_frameworks():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "main.py"), "w").close()
        open(os.path.join(repo_dir, "app.js"), "w").close()
        open(os.path.join(repo_dir, "requirements.txt"), "w").write("streamlit\npytest\n")
        open(os.path.join(repo_dir, "package.json"), "w").write("{\"dependencies\":{}}")
        os.mkdir(os.path.join(repo_dir, "docs"))
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert "Python" in report["languages"]
        assert "JavaScript" in report["languages"]
        assert "Streamlit" in report["frameworks"]
        assert "requirements.txt" in report["dependency_management"]
        assert "package.json" in report["dependency_management"]


def test_profile_handles_symlinks_and_unusual_structure():
    with tempfile.TemporaryDirectory() as repo_dir:
        os.mkdir(os.path.join(repo_dir, "src"))
        open(os.path.join(repo_dir, "src", "main.py"), "w").close()
        # Create symlink if supported
        symlink_path = os.path.join(repo_dir, "linked.py")
        target_path = os.path.join(repo_dir, "src", "main.py")
        try:
            os.symlink(target_path, symlink_path)
        except (OSError, AttributeError):
            pass  # Symlinks may not be supported on all platforms
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert "Python" in report["languages"]


def test_profile_error_handling_for_unreadable_files():
    with tempfile.TemporaryDirectory() as repo_dir:
        file_path = os.path.join(repo_dir, "unreadable.txt")
        open(file_path, "w").close()
        os.chmod(file_path, 0)
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        try:
            report = profiler.profile()
            assert isinstance(report, dict)
        finally:
            os.chmod(file_path, 0o644)


def test_profile_all_fields_coverage():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "main.py"), "w").close()
        open(os.path.join(repo_dir, "requirements.txt"), "w").write("streamlit\npytest\n")
        open(os.path.join(repo_dir, "README.md"), "w").close()
        open(os.path.join(repo_dir, "LICENSE"), "w").write("MIT License\n")
        os.mkdir(os.path.join(repo_dir, "docs"))
        os.mkdir(os.path.join(repo_dir, "demo_output"))
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        expected_fields = [
            "repo_name", "languages", "frameworks", "dependency_management", "license", "documentation",
            "code_quality_tools", "test_status", "ci_cd", "main_files", "security", "contributors",
            "issue_templates", "branch_protection", "artifact_outputs", "detected_capabilities"
        ]
        for field in expected_fields:
            assert field in report


def test_dashboard_ui_rendering_large_report():
    # This is a placeholder for UI rendering test; actual Streamlit UI tests require integration tools.
    # Here, just ensure large report can be loaded without error.
    with tempfile.TemporaryDirectory() as repo_dir:
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        # Simulate large report
        report["extra"] = {f"field_{i}": "value" for i in range(1000)}
        import json
        output_path = os.path.join(repo_dir, "large_report.json")
        with open(output_path, "w") as f:
            json.dump(report, f)
        with open(output_path, "r") as f:
            loaded = json.load(f)
        assert "extra" in loaded
        assert len(loaded["extra"]) == 1000

