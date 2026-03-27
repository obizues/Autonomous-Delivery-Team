import importlib.util
import os
main_src = os.path.abspath(os.path.join(os.path.dirname(__file__), 'file_validator.py'))
spec = importlib.util.spec_from_file_location("file_validator", main_src)
file_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_validator)
MAX_FILE_SIZE_BYTES = file_validator.MAX_FILE_SIZE_BYTES

class UploadResult:
    def __init__(self, status, error=None):
        self.status = status
        self.error = error

def upload_document(filename, content):
    if len(content) > MAX_FILE_SIZE_BYTES:
        return UploadResult("REJECTED", error="file_too_large")
    return UploadResult("ACCEPTED")

