"""
Role-based access control utilities for the backend.
"""
from fastapi import HTTPException, status
from .models import UserRole, User as DBUser
from .schemas import User

def require_admin(current_user: DBUser) -> None:
    """
    Dependency function to require admin role.
    Raises HTTPException if user is not an admin.
    
    Usage in routes:
        @router.get("/admin-only")
        def admin_only_route(current_user: DBUser = Depends(get_current_user)):
            require_admin(current_user)
            # Admin-only logic here
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

def is_admin(current_user: DBUser) -> bool:
    """
    Check if the current user has admin role.
    
    Args:
        current_user: The database user object
        
    Returns:
        bool: True if user is admin, False otherwise
    """
    return current_user.role == UserRole.admin

def is_owner_or_admin(resource_owner_id: int, current_user: DBUser) -> bool:
    """
    Check if the current user is the owner of a resource or an admin.
    
    Args:
        resource_owner_id: The ID of the resource owner
        current_user: The current logged-in user
        
    Returns:
        bool: True if user is owner or admin, False otherwise
    """
    return current_user.id == resource_owner_id or current_user.role == UserRole.admin

def require_owner_or_admin(resource_owner_id: int, current_user: DBUser) -> None:
    """
    Require that the current user is either the owner of a resource or an admin.
    Raises HTTPException if neither condition is met.
    
    Args:
        resource_owner_id: The ID of the resource owner
        current_user: The current logged-in user
        
    Raises:
        HTTPException: 403 if user is neither owner nor admin
    """
    if not is_owner_or_admin(resource_owner_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
