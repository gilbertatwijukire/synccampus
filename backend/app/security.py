import hashlib, hmac, os, secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import config
from .database import get_db
from .models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
        new = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(new.hex(), dk)
    except Exception:
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        user = db.get(User, int(data["sub"]))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account disabled")
    return user


def require_roles(*roles):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this resource")
        return user
    return dep


# ---- student access codes (never stored; only a keyed hash is kept) ----
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_access_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(12))
    return "-".join(raw[i:i + 4] for i in range(0, 12, 4))


def new_reference() -> str:
    return "SC-" + "".join(secrets.choice(_ALPHABET) for _ in range(6))


def hash_code(code: str) -> str:
    clean = code.strip().upper().replace(" ", "")
    return hashlib.sha256((config.ACCESS_CODE_PEPPER + clean).encode()).hexdigest()
