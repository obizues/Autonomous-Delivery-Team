from auth_models import AuthResult
def create_token(username: str) -> str:
    return f"token:{username}"
