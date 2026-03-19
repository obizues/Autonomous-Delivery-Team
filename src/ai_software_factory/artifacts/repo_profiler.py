# src/ai_software_factory/artifacts/repo_profiler.py

import os
import json
from typing import Dict, Any, List

class RepoCapabilityProfiler:
    """
    Profiles a repository and generates a structured capability report artifact.
    """
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def profile(self) -> Dict[str, Any]:
        report = {
            "repo_name": os.path.basename(self.repo_path),
            "languages": self.extract_languages(),
            "frameworks": self.detect_frameworks(),
            "dependency_management": self.find_dependency_files(),
            "license": self.find_license(),
            "documentation": self.find_docs(),
            "code_quality_tools": self.find_code_quality_tools(),
            "test_status": self.find_tests(),
            "ci_cd": self.find_ci_cd(),
            "main_files": self.find_main_files(),
            "security": self.find_security(),
            "contributors": self.find_contributors(),
            "issue_templates": self.find_issue_templates(),
            "branch_protection": self.find_branch_protection(),
            "artifact_outputs": self.find_artifact_outputs(),
            "detected_capabilities": self.summarize_capabilities(),
        }
        return report

    def extract_languages(self) -> List[str]:
        exts = set()
        for root, _, files in os.walk(self.repo_path):
            for f in files:
                if f.endswith('.py'): exts.add('Python')
                if f.endswith('.js'): exts.add('JavaScript')
                if f.endswith('.ts'): exts.add('TypeScript')
                if f.endswith('.md'): exts.add('Markdown')
        return list(exts)

    def detect_frameworks(self) -> List[str]:
        frameworks = []
        if os.path.exists(os.path.join(self.repo_path, 'requirements.txt')):
            with open(os.path.join(self.repo_path, 'requirements.txt')) as f:
                reqs = f.read().lower()
                if 'streamlit' in reqs: frameworks.append('Streamlit')
                if 'pytest' in reqs: frameworks.append('Pytest')
        return frameworks

    def find_dependency_files(self) -> List[str]:
        files = []
        for fname in ['requirements.txt', 'pyproject.toml', 'package.json']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                files.append(fname)
        return files

    def find_license(self) -> str:
        for fname in ['LICENSE', 'LICENSE.txt', 'LICENSE.md']:
            path = os.path.join(self.repo_path, fname)
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        line = f.readline().strip()
                        if line:
                            return line
                        else:
                            return 'None'
                except Exception:
                    return 'Error'
        return 'None'

    def find_docs(self) -> List[str]:
        docs = []
        for fname in ['README.md', 'docs']:
            path = os.path.join(self.repo_path, fname)
            if os.path.exists(path): docs.append(fname)
        return docs

    def find_code_quality_tools(self) -> List[str]:
        tools = []
        for fname in ['.flake8', '.pylintrc', '.editorconfig']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                tools.append(fname)
        return tools

    def find_tests(self) -> str:
        for fname in ['tests', 'pytest.ini', 'test', 'scripts/demo_acceptance.py']:
            path = os.path.join(self.repo_path, fname)
            if os.path.exists(path):
                return f"{fname} detected"
        return 'None'

    def find_ci_cd(self) -> str:
        for fname in ['.github/workflows', 'launch.bat', 'Dockerfile']:
            path = os.path.join(self.repo_path, fname)
            if os.path.exists(path):
                return f"{fname} found"
        return 'None'

    def find_main_files(self) -> List[str]:
        mains = []
        for fname in ['ui/launcher.py', 'ui/app.py', '__main__.py']:
            path = os.path.join(self.repo_path, fname)
            if os.path.exists(path): mains.append(fname)
        return mains

    def find_security(self) -> List[str]:
        files = []
        for fname in ['SECURITY.md', '.github/SECURITY.md']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                files.append(fname)
        return files

    def find_contributors(self) -> List[str]:
        files = []
        for fname in ['.github/CODEOWNERS', '.github/CONTRIBUTING.md']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                files.append(fname)
        return files

    def find_issue_templates(self) -> List[str]:
        files = []
        for fname in ['.github/ISSUE_TEMPLATE', '.github/PULL_REQUEST_TEMPLATE.md']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                files.append(fname)
        return files

    def find_branch_protection(self) -> str:
        if os.path.exists(os.path.join(self.repo_path, '.github/workflows')):
            return 'CI/CD workflows found'
        return 'None'

    def find_artifact_outputs(self) -> List[str]:
        outputs = []
        for fname in ['demo_output', 'generated_workspace', 'build', 'dist']:
            if os.path.exists(os.path.join(self.repo_path, fname)):
                outputs.append(fname)
        return outputs

    def summarize_capabilities(self) -> List[str]:
        caps = []
        if 'Streamlit' in self.detect_frameworks(): caps.append('dashboard')
        if 'Pytest' in self.detect_frameworks(): caps.append('testing')
        if os.path.exists(os.path.join(self.repo_path, 'docs')): caps.append('documentation')
        if os.path.exists(os.path.join(self.repo_path, 'ui/launcher.py')): caps.append('workflow engine')
        return caps

    def save_report(self, output_path: str):
        import tempfile, os
        report = self.profile()
        dir_name = os.path.dirname(output_path) or '.'
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tmp:
            json.dump(report, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp.name, output_path)

# Example usage:
# profiler = RepoCapabilityProfiler(repo_path="../")
# profiler.save_report("repo_capability_report.json")
