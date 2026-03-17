from ai_classifier import classify_document
from file_validator import validate_extension
from models import UploadResult
from suspicion_evaluator import is_suspicious


def upload_document(filename: str, content: bytes) -> UploadResult:
    if not validate_extension(filename):
        return UploadResult(status="REJECTED", message="Upload rejected")

    classification = classify_document(content)
    suspicious = is_suspicious(classification)
    if suspicious:
        return UploadResult(status="FLAGGED_FOR_REVIEW", message="Upload flagged")

    return UploadResult(
        status="ACCEPTED",
        message="Upload accepted",
        category=classification["category"],
        confidence=classification["confidence"],
    )
