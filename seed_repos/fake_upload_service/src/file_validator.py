ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg"}


def validate_extension(filename: str) -> bool:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in ALLOWED_EXTENSIONS
