import pathlib
import sys
sandbox_path = str(pathlib.Path(__file__).resolve().parents[3] / "sandbox_repos")
sys.path = [p for p in sys.path if sandbox_path not in p]
src_path = str(pathlib.Path(__file__).resolve().parents[1] / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import importlib
auth_service = importlib.import_module("auth_service")
login = auth_service.login


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
