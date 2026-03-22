from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import audit, get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, TokenResponse, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    await audit(db, user.id, "LOGIN", ip_addr=request.client.host if request.client else None)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, must_change_password=user.must_change_password)


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.post("/change-password")
async def change_password(
    body: PasswordChange,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong current password")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password too short (min 6)")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    await audit(db, user.id, "PASSWORD_CHANGE", ip_addr=request.client.host if request.client else None)
    await db.commit()
    return {"message": "Password changed successfully"}
