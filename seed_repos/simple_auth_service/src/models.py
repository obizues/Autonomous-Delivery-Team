from dataclasses import dataclass


@dataclass
class AuthResult:
    status: str
    message: str
    token: str | None = None
    error: str | None = None
