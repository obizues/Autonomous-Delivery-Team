import pytest
from ai_software_factory.orchestration.multi_repo import MultiRepoCoordinator


def test_multi_repo_ingestion_and_profiling():
    coordinator = MultiRepoCoordinator()
    repos = ["repo1", "repo2"]
    profiles = coordinator.profile_repos(repos)
    assert len(profiles) == 2
    for profile in profiles:
        assert "repo_name" in profile
        assert "languages" in profile


def test_multi_repo_artifact_linking():
    coordinator = MultiRepoCoordinator()
    repo_artifacts = {"repo1": ["artifactA"], "repo2": ["artifactB"]}
    links = coordinator.link_artifacts(repo_artifacts)
    assert "repo1" in links
    assert "repo2" in links
    assert links["repo1"] == ["artifactA"]
    assert links["repo2"] == ["artifactB"]

