import importlib.util
import os
import sys
import pathlib
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
file_validator_path = os.path.join(main_dir, 'file_validator.py')
upload_service_path = os.path.join(main_dir, 'upload_service.py')
spec_fv = importlib.util.spec_from_file_location("file_validator", file_validator_path)
file_validator = importlib.util.module_from_spec(spec_fv)
spec_fv.loader.exec_module(file_validator)
spec_us = importlib.util.spec_from_file_location("upload_service", upload_service_path)
upload_service = importlib.util.module_from_spec(spec_us)
spec_us.loader.exec_module(upload_service)
MAX_FILE_SIZE_BYTES = file_validator.MAX_FILE_SIZE_BYTES
upload_document = upload_service.upload_document

def test_rejected_payload_includes_reason_for_oversized_files():
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    result = upload_document("large.pdf", oversized)
    assert result.status == "REJECTED"
    assert result.error == "file_too_large"

def test_valid_files_continue_to_upload():
    result = upload_document("valid.pdf", b"invoice payload")
    assert result.status in {"ACCEPTED", "FLAGGED_FOR_REVIEW"}
