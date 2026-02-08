import os
from slowapi import Limiter
from fastapi import Request

# P1-8 FIX: Allow disabling rate limiting in dev/test environments.
# slowapi uses in-memory storage that resets on --reload (dev mode).
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")


def _get_user_rate_limit_key(request: Request) -> str:
    """Rate limit by authenticated user ID, not IP address.

    Docker Compose bridge network causes all clients to share the Docker
    gateway IP — IP-based limiting would treat all users as one client.
    We extract the user_id from the session cookie (set by get_current_user
    dependency). Each authenticated user gets a separate rate limit bucket.

    If no session exists, the Depends(get_current_user) dependency will
    have already returned 401 Unauthorized before the rate limiter runs,
    so the fallback should never be reached in practice."""
    user_id = request.session.get("user_id") if hasattr(request, 'session') else None
    if user_id:
        return f"user:{user_id}"
    # Fallback to IP if no session (shouldn't happen for authenticated endpoints)
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=_get_user_rate_limit_key,
    enabled=RATE_LIMIT_ENABLED,
)
