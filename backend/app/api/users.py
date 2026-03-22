from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import hash_password
from app.models.topology import Group
from app.models.user import User, UserRole
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    must_change_password: bool = False


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    must_change_password: bool | None = None


class BulkDeleteRequest(BaseModel):
    ids: list[int]


def _check_can_manage(actor: User, target_role: UserRole):
    """Actor can only manage users with strictly lower level."""
    if target_role.level() >= actor.role.level():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot manage users with role {target_role.value}",
        )


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List users whose role level is strictly below the current user's."""
    result = await db.execute(select(User))
    all_users = result.scalars().all()
    return [u for u in all_users if u.role.level() < current_user.role.level()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _check_can_manage(current_user, body.role)

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        must_change_password=body.must_change_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Cannot modify users at same or higher level
    _check_can_manage(current_user, target.role)

    # Cannot promote to same or higher level than self
    if body.role is not None:
        _check_can_manage(current_user, body.role)

    if body.username is not None:
        existing = await db.execute(
            select(User).where(User.username == body.username, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already exists")
        target.username = body.username

    if body.password is not None:
        target.password_hash = hash_password(body.password)
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.must_change_password is not None:
        target.must_change_password = body.must_change_password

    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    _check_can_manage(current_user, target.role)

    await db.delete(target)
    await db.commit()


@router.get("/{user_id}/groups")
async def get_user_groups(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get group IDs this user can access (empty = all groups)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _check_can_manage(current_user, target.role)
    return {"group_ids": [g.id for g in target.accessible_groups]}


@router.put("/{user_id}/groups", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_groups(
    user_id: int,
    body: BulkDeleteRequest,  # reuse ids field: list[int] = group IDs
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Set accessible groups for a user (empty list = access to all groups)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _check_can_manage(current_user, target.role)

    # Resolve group objects
    groups: list[Group] = []
    if body.ids:
        g_result = await db.execute(select(Group).where(Group.id.in_(body.ids)))
        groups = list(g_result.scalars().all())

    target.accessible_groups = groups
    await db.commit()


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_users(
    body: BulkDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id.in_(body.ids)))
    targets = result.scalars().all()
    for target in targets:
        _check_can_manage(current_user, target.role)
        await db.delete(target)
    await db.commit()
