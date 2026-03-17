from models import AuthResult
from token_store import create_token


USERS = {
    "alice": "secret123",
    "bob": "hunter2",
}


def login(username: str, password: str) -> AuthResult:
    expected = USERS.get(username)
    if expected is None:
        return AuthResult(status="DENIED", message="Unknown user", error="unknown_user")

    if password != expected:
        return AuthResult(status="DENIED", message="Invalid credentials", error="invalid_credentials")

    return AuthResult(
        status="AUTHENTICATED",
        message="Login successful",
        token=create_token(username),
    )
