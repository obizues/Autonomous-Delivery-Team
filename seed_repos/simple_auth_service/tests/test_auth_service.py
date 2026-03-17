import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from auth_service import login


def test_unknown_user_denied():
    result = login("unknown", "pw")
    assert result.status == "DENIED"
    assert result.error == "unknown_user"


def test_invalid_password_denied():
    result = login("alice", "wrong")
    assert result.status == "DENIED"
    assert result.error == "invalid_credentials"


def test_valid_user_authenticated():
    result = login("alice", "secret123")
    assert result.status == "AUTHENTICATED"
    assert result.token == "token:alice"
