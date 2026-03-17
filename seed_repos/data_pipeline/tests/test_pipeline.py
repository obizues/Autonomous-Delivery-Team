import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from pipeline import process_records


def test_process_valid_records():
    result = process_records([
        {"id": "a1", "amount": "12.5"},
        {"id": "a2", "amount": 8},
    ])
    assert len(result["accepted"]) == 2
    assert result["accepted"][0]["status"] == "processed"


def test_reject_invalid_records():
    result = process_records([
        {"id": "a1", "amount": "12.5"},
        {"amount": "7"},
    ])
    assert len(result["accepted"]) == 1
    assert len(result["rejected"]) == 1
