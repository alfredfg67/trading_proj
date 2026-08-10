from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserCreate, UserResponse
from app.dal.base import DatabaseError
from app.core.rate_limit import limiter

router = APIRouter(tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")   # rate limit per IP
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch user by email
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    if not user:
        # Delay to avoid timing attacks (still return 401)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Check if user is locked (before checking password)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    if user.is_locked:
        raise HTTPException(status_code=403, detail="Account locked, contact support")

    # 3. Verify password
    if not verify_password(login_data.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 3:
            user.is_locked = True
            user.locked_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 4. Successful login – reset failed attempts, update last_login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # 5. Generate tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# ... (refresh and logout endpoints remain the same as Phase 2) ...

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(refresh_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_locked:
        raise HTTPException(status_code=403, detail="User not active or locked")

    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout():
    return {"detail": "Logged out"}