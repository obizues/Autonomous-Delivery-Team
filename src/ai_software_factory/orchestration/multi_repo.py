class MultiRepoCoordinator:
    repo_profiles: list

    # Only one __init__ method should exist; remove duplicate

    def match_capabilities(self, required_capabilities):
        """
        Return repos that match required capabilities.
        """
        matched = []
        for profile in self.repo_profiles:
            if all(cap in profile.get("capabilities", []) for cap in required_capabilities):
                matched.append(profile.get("repo_name", profile.get("name")))
        return matched

    def select_best_repo(self, task_description, required_capabilities):
        """
        Select the best repo for a task based on capability matching.
        """
        matched = self.match_capabilities(required_capabilities)
        if matched:
            return matched[0]
        return self.select_repo_for_task(task_description)
    def __init__(self, repo_profiles=None):
        self.repo_profiles = repo_profiles or []

    def profile_repos(self, repos):
        # Stub: Return fake profiles for each repo with capabilities
        self.repo_profiles = [
            {"repo_name": repo, "languages": ["Python"], "capabilities": ["upload", "auth", "pipeline"]} for repo in repos
        ]
        return self.repo_profiles

    def select_repo_for_task(self, task_description):
        # Agentic selection: choose repo based on task and capabilities
        for profile in self.repo_profiles:
            if any(cap in task_description for cap in profile.get("capabilities", [])):
                return profile["repo_name"]
        return self.repo_profiles[0]["repo_name"] if self.repo_profiles else None

    def route_task(self, task_description):
        # Route task to selected repo
        repo = self.select_repo_for_task(task_description)
        return repo

    def link_artifacts(self, repo_artifacts):
        # Stub: Return input mapping as links
        return repo_artifacts
