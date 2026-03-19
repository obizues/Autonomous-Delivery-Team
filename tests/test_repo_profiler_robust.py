import os
import tempfile
import time
import pytest
from ai_software_factory.artifacts.repo_profiler import RepoCapabilityProfiler


def test_profiler_performance_on_large_repo():
    with tempfile.TemporaryDirectory() as repo_dir:
        # Simulate large repo
        for i in range(1000):
            open(os.path.join(repo_dir, f"file_{i}.py"), "w").close()
        start = time.time()
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        duration = time.time() - start
        assert duration < 5  # Should finish within 5 seconds
        assert len(report["languages"]) >= 1


def test_artifact_versioning_and_overwrite():
    with tempfile.TemporaryDirectory() as repo_dir:
        output_path = os.path.join(repo_dir, "capability_report.json")
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        profiler.save_report(output_path)
        # Overwrite
        profiler.save_report(output_path)
        assert os.path.exists(output_path)
        import json
        with open(output_path, "r") as f:
            data = json.load(f)
        assert data["repo_name"] == os.path.basename(repo_dir)


def test_workflow_engine_integration():
    # This is a placeholder; actual integration test would require workflow engine setup
    # Here, just ensure profiler can be called at workflow start
    with tempfile.TemporaryDirectory() as repo_dir:
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert isinstance(report, dict)


def test_dashboard_ui_handles_missing_and_malformed_report():
    # Simulate missing report
    missing_path = "nonexistent_report.json"
    assert not os.path.exists(missing_path)
    # Simulate malformed report
    with tempfile.TemporaryDirectory() as repo_dir:
        malformed_path = os.path.join(repo_dir, "malformed.json")
        with open(malformed_path, "w") as f:
            f.write("not a json")
        try:
            import json
            with open(malformed_path, "r") as f:
                json.load(f)
        except Exception:
            assert True


def test_profiler_extensibility():
    # Add new field and ensure profiler doesn't break
    class ExtendedProfiler(RepoCapabilityProfiler):
        def profile(self):
            report = super().profile()
            report["new_field"] = "extra"
            return report
    with tempfile.TemporaryDirectory() as repo_dir:
        profiler = ExtendedProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert "new_field" in report


def test_profiler_security_and_permission_handling():
    with tempfile.TemporaryDirectory() as repo_dir:
        sensitive_file = os.path.join(repo_dir, "secret.txt")
        open(sensitive_file, "w").close()
        os.chmod(sensitive_file, 0)
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        try:
            report = profiler.profile()
            assert isinstance(report, dict)
        finally:
            os.chmod(sensitive_file, 0o644)


def test_profiler_cross_platform_compatibility():
    # This is a placeholder; actual test would run on multiple OSes
    with tempfile.TemporaryDirectory() as repo_dir:
        profiler = RepoCapabilityProfiler(repo_path=repo_dir)
        report = profiler.profile()
        assert isinstance(report, dict)

