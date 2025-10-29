from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status, Security

# Create the security scheme (same as IRB Assistant)
security = HTTPBearer(auto_error=False)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials = None
) -> str:
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization header missing"
        )
    
    # credentials.credentials contains the token (without "Bearer ")
    api_key = credentials.credentials.strip()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is empty"
        )
    
    return api_key