from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from typing import Optional
from ..database import get_db
from .. import crud, models, schemas
from ..dependencies import get_current_user
from ..rbac import require_admin

router = APIRouter()

@router.post("/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await crud.create_user(db, user)

@router.post("/login")
async def login(request: Request, user_credentials: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await crud.authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    request.session["user_id"] = user.id
    return {"message": "Login successful"}

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logout successful"}

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/departments")
async def get_departments(db: AsyncSession = Depends(get_db)):
    departments = await crud.get_departments(db)
    return [{"id": dept.id, "name": dept.name} for dept in departments]

@router.get("/users", response_model=list[schemas.UserBasic])
async def list_users(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get list of all users (excluding current user) with optional search."""
    users = await crud.get_all_users(db, exclude_user_id=current_user.id, search=search)
    return users

@router.put("/change-password")
async def change_password(
    password_data: schemas.PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Change current user's password."""
    # Verify current password
    user = await crud.authenticate_user(db, current_user.username, password_data.current_password)
    if not user:
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Update password
    success = await crud.update_user_password(db, current_user.id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    return {"message": "Password changed successfully"}

@router.put("/profile", response_model=schemas.User)
async def update_profile(
    profile_data: schemas.ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update current user's profile information."""
    # For admins, allow full profile editing
    if current_user.role == models.UserRole.admin:
        user_update = {
            "email": profile_data.email,
            "first_name": profile_data.first_name,
            "last_name": profile_data.last_name,
            "department_id": profile_data.department_id
        }
        updated_user = await crud.update_user(db, current_user.id, user_update)
        if not updated_user:
            raise HTTPException(status_code=500, detail="Failed to update profile")
        return updated_user
    else:
        # Regular users can only change password via change-password endpoint
        raise HTTPException(status_code=403, detail="Only admins can update profile information")

@router.get("/users/{user_id}", response_model=schemas.User)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get specific user details (admin only)."""
    require_admin(current_user)
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: int,
    user_data: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update user profile (admin only)."""
    require_admin(current_user)
    
    # Check if user exists
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for username conflicts
    if user_data.username != user.username:
        existing_user = await crud.get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Update user
    user_update = {
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "username": user_data.username,
        "role": user_data.role,
        "department_id": user_data.department_id
    }
    updated_user = await crud.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update user")
    
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a user (admin only)."""
    require_admin(current_user)
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user exists
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user
    success = await crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    return {"message": "User deleted successfully"}

@router.put("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: schemas.PasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Reset a user's password (admin only)."""
    require_admin(current_user)
    
    # Check if user exists
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    success = await crud.update_user_password(db, user_id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset password")
    
    return {"message": "Password reset successfully"}
