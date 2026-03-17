from __future__ import annotations

from pathlib import Path


class FileWriter:
    def write_files(self, root: Path, files: dict[str, str]) -> list[str]:
        written: list[str] = []
        for relative_path, content in files.items():
            output = root / relative_path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content.rstrip() + "\n", encoding="utf-8")
            written.append(relative_path)
        return written
