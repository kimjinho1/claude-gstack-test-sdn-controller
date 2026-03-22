from pydantic import BaseModel

from app.models.user import UserRole


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
