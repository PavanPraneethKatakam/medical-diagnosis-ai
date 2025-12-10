"""
Security utilities for API protection

Implements rate limiting, authentication, and input validation.
"""

from fastapi import HTTPException, Security, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from collections import defaultdict
from datetime import datetime, timedelta
import secrets
import os
from typing import Optional


# Basic Auth
security = HTTPBasic()

# Rate limiting storage (in-memory, use Redis for production)
_rate_limit_storage = defaultdict(list)


def get_current_username(credentials: HTTPBasicCredentials = Security(security)) -> str:
    """
    Validate basic auth credentials.
    
    Args:
        credentials: HTTP Basic credentials
        
    Returns:
        Username if valid
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Get credentials from environment or use defaults (CHANGE IN PRODUCTION!)
    correct_username = os.getenv("AUTH_USERNAME", "admin")
    correct_password = os.getenv("AUTH_PASSWORD", "changeme123")
    
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        correct_username.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


def check_rate_limit(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 60
) -> None:
    """
    Simple token bucket rate limiting per IP.
    
    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = request.client.host
    now = datetime.now()
    cutoff = now - timedelta(seconds=window_seconds)
    
    # Clean old requests
    _rate_limit_storage[client_ip] = [
        req_time for req_time in _rate_limit_storage[client_ip]
        if req_time > cutoff
    ]
    
    # Check limit
    if len(_rate_limit_storage[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds."
        )
    
    # Add current request
    _rate_limit_storage[client_ip].append(now)


def validate_file_upload(
    filename: str,
    file_size: int,
    max_size_mb: int = 5,
    allowed_extensions: set = {'.pdf', '.txt'}
) -> str:
    """
    Validate file upload for security.
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        max_size_mb: Maximum file size in MB
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        Sanitized filename
        
    Raises:
        HTTPException: If validation fails
    """
    import re
    from pathlib import Path
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size_mb}MB."
        )
    
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Sanitize filename (remove special chars, path traversal)
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    safe_filename = safe_filename.replace('..', '_')
    
    # Prevent empty filename
    if not safe_filename or safe_filename.startswith('.'):
        safe_filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    
    return safe_filename
