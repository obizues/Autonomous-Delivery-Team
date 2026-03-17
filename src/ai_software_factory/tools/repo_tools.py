from __future__ import annotations

from pathlib import Path


def list_repo_files(repo_path: str | Path) -> list[str]:
    root = Path(repo_path)
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*.py")
        if path.is_file()
    )


def search_repo(repo_path: str | Path, keyword: str) -> list[str]:
    root = Path(repo_path)
    matches: list[str] = []
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if keyword.lower() in text.lower():
            matches.append(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(matches)


def read_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def get_test_files(repo_path: str | Path) -> list[str]:
    root = Path(repo_path)
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("test_*.py")
        if path.is_file()
    )
