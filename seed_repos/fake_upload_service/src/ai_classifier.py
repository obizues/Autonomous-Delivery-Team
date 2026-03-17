def classify_document(content: bytes) -> dict:
    payload = content.lower()
    if b"invoice" in payload:
        return {"category": "finance", "confidence": 0.84, "suspicion_score": 0.1}
    return {"category": "general", "confidence": 0.78, "suspicion_score": 0.2}
