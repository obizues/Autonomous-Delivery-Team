

import importlib.util
import os
main_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'file_validator.py'))
spec = importlib.util.spec_from_file_location("file_validator", main_src)
file_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_validator)
validate_extension = file_validator.validate_extension
validate_upload = file_validator.validate_upload
MAX_FILE_SIZE_BYTES = file_validator.MAX_FILE_SIZE_BYTES

def test_validate_extension():
    assert validate_extension("file.pdf") is True
    assert validate_extension("photo.png") is True
    assert validate_extension("payload.exe") is False

def test_unsupported_file_type():
    is_valid, reason = validate_upload("file.exe", b"dummy")
    assert is_valid is False
    assert reason == "unsupported_file_type"

def test_oversized_file_rejection():
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    is_valid, reason = validate_upload("large.pdf", oversized)
    assert is_valid is False
    assert reason == "file_too_large"
