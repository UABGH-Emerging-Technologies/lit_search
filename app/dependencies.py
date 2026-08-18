import hmac
import os

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Create the security scheme (same as IRB Assistant)
security = HTTPBearer(auto_error=False)


async def get_api_key(credentials: HTTPAuthorizationCredentials = None) -> str:
    """
    Extract API key from Authorization header.
    Returns the API key if present, raises 403 if missing or invalid.

    Args:
        credentials: HTTPAuthorizationCredentials from Security(security)

    Returns:
        str: The API key from the Authorization header

    Raises:
        HTTPException: 403 if authorization missing or invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Authorization header missing"
        )

    # credentials.credentials contains the token (without "Bearer ")
    api_key = credentials.credentials.strip()

    if not api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is empty")

    return api_key


async def require_gateway_key(
    x_gateway_key: str = Header(default=None, alias="X-Gateway-Key"),
) -> None:
    """
    Enforce an optional shared gateway key on protected routers.

    Reads the expected key from the `LIT_GATEWAY_API_KEY` environment variable. If
    it is unset or empty, gateway authentication is disabled and the dependency
    passes. Otherwise the `X-Gateway-Key` request header must be present and match
    the expected value (compared in constant time).

    Args:
        x_gateway_key: The value of the `X-Gateway-Key` request header.

    Returns:
        None

    Raises:
        HTTPException: 401 if the gateway key is enabled and missing or mismatched.
    """
    expected = os.environ.get("LIT_GATEWAY_API_KEY", "")
    if not expected:
        return None

    if x_gateway_key is None or not hmac.compare_digest(x_gateway_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing gateway key",
        )
    return None
