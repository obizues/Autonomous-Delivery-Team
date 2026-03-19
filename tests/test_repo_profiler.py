import os
import tempfile
import shutil
import pytest
from ai_software_factory.artifacts.repo_profiler import RepoCapabilityProfiler


def test_profile_minimal_python_repo():
    with tempfile.TemporaryDirectory() as repo_dir:
        # Create minimal Python repo structure
        open(os.path.join(repo_dir, "main.py"), "w").close()
        open(os.path.join(repo_dir, "requirements.txt"), "w").write("streamlit\npytest\n")
        open(os.path.join(repo_dir, "README.md"), "w").close()
        os.mkdir(os.path.join(repo_dir, "docs"))
        os.mkdir(os.path.join(repo_dir, "demo_output"))
        # Run profiler
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert "Python" in report["languages"]
        assert "Streamlit" in report["frameworks"]
        assert "requirements.txt" in report["dependency_management"]
        assert "README.md" in report["documentation"]
        assert "dashboard" in report["detected_capabilities"]
        assert "demo_output" in report["artifact_outputs"]


def test_save_report_creates_json():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "main.py"), "w").close()
        output_path = os.path.join(repo_dir, "capability_report.json")
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        profiler.save_report(output_path)
        assert os.path.exists(output_path)
        import json
        with open(output_path, "r") as f:
            data = json.load(f)
        assert data["repo_name"] == os.path.basename(repo_dir)


def test_profile_detects_license_and_tests():
    with tempfile.TemporaryDirectory() as repo_dir:
        open(os.path.join(repo_dir, "LICENSE"), "w").write("MIT License\n")
        os.mkdir(os.path.join(repo_dir, "tests"))
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert report["license"].startswith("MIT")
        assert report["test_status"].startswith("tests detected")


def test_profile_handles_empty_repo():
    with tempfile.TemporaryDirectory() as repo_dir:
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert isinstance(report, dict)
        assert report["languages"] == []
        assert report["frameworks"] == []
        assert report["dependency_management"] == []
        assert report["documentation"] == []
        assert report["artifact_outputs"] == []

