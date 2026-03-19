class MultiRepoCoordinator:
    def profile_repos(self, repos):
        # Stub: Return fake profiles for each repo
        return [
            {"repo_name": repo, "languages": ["Python"]} for repo in repos
        ]

    def link_artifacts(self, repo_artifacts):
        # Stub: Return input mapping as links
        return repo_artifacts
