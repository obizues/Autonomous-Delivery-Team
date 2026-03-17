import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from upload_service import upload_document


def test_upload_accepts_valid_document():
    result = upload_document("invoice.pdf", b"invoice 2026")
    assert result.status == "ACCEPTED"
    assert result.error is None


def test_upload_rejects_invalid_extension():
    result = upload_document("malware.exe", b"bad")
    assert result.status == "REJECTED"
