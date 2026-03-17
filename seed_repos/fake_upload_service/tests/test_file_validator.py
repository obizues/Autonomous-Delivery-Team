import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from file_validator import validate_extension


def test_validate_extension_accepts_supported_types():
    assert validate_extension("sample.pdf") is True
    assert validate_extension("photo.png") is True


def test_validate_extension_rejects_unsupported_types():
    assert validate_extension("payload.exe") is False
