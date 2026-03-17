from dataclasses import dataclass


@dataclass
class UploadResult:
    status: str
    message: str
    error: str | None = None
    category: str | None = None
    confidence: float | None = None
