from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.database import get_db
from app.api.v1.deps import require_admin, get_current_user
from app.models.user import User, UserRole
from app.schemas.admin import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.core.security import hash_password
from app.dal.base import DatabaseError
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (admin only)."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed = hash_password(user_data.password)
    
    new_user = User(
        email=user_data.email,
        password_hash=hashed,
        role=user_data.role or UserRole.USER,
        phone=user_data.phone,
        whatsapp=user_data.whatsapp,
        telegram=user_data.telegram,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.patch("/users/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Unlock a user account (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_at = None
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_role(
    user_id: int,
    role_data: dict,  # {"role": "admin" or "user"}
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a user's role (admin only)."""
    new_role = role_data.get("role")
    if new_role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft‑delete a user (set is_active=False) (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()

@router.post("/users/{user_id}/reset-password", response_model=dict)
async def reset_password(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset a user's password (admin only).
    Returns a temporary password (for simplicity; in production you'd send an email).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate a random temporary password
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Hash and save
    user.password_hash = hash_password(temp_password)
    await db.commit()
    
    return {"temporary_password": temp_password}