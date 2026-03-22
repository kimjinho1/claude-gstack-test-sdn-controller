from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet key derived from MASTER_SECRET (pad/hash to 32 bytes, then base64url)
import base64
import hashlib

_key_bytes = hashlib.sha256(settings.MASTER_SECRET.encode()).digest()
_fernet_key = base64.urlsafe_b64encode(_key_bytes)
_fernet = Fernet(_fernet_key)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def encrypt_credential(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_credential(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
