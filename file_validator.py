ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

def validate_extension(filename: str) -> bool:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in ALLOWED_EXTENSIONS

def validate_upload(filename: str, content: bytes) -> tuple[bool, str]:
    if not validate_extension(filename):
        return False, "unsupported_file_type"
    if len(content) > MAX_FILE_SIZE_BYTES:
        return False, "file_too_large"
    return True, "ok"
