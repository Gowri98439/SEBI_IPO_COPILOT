from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_user_or_ip(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from app.utils.security import decode_token
            payload = decode_token(token)
            if "sub" in payload:
                return payload["sub"]
        except Exception:
            pass
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)
