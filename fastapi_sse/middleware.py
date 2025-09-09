# fastapi_sse/middleware.py
from fastapi import Request
from typing import Optional, Callable, Coroutine, Any

# Provide a helper to build auth hooks that the user can plug into SSEManager
def token_auth_hook_factory(token_lookup: Callable[[str], Optional[str]]):
    """
    token_lookup: callable(token_str) -> user_id | None
    Returns a coroutine-compatible hook for SSEManager.
    """
    async def hook(request: Request) -> Optional[str]:
        auth = request.headers.get("Authorization")
        if not auth:
            return None
        # Accept "Bearer <token>"
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = auth
        user_id = token_lookup(token)
        return user_id
    return hook
