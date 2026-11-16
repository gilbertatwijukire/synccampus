from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Delegate
from ..schemas import UserIn
from ..security import verify_password, create_token, current_user, require_roles, hash_password
from .. import services

router = APIRouter(prefix="/api", tags=["staff-auth"])


@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    services.audit(db, user, "login", "user", user.id); db.commit()
    return {"access_token": create_token(user), "token_type": "bearer",
            "user": {"id": user.id, "name": user.full_name, "role": user.role}}


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.full_name, "role": user.role,
            "delegate_id": user.delegate.id if user.delegate else None}


@router.post("/admin/users", status_code=201)
def create_user(data: UserIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if data.role not in ("president", "delegate", "admin"):
        raise HTTPException(400, "Role must be president, delegate or admin")
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    u = User(full_name=data.full_name, email=data.email.lower(), password_hash=hash_password(data.password), role=data.role)
    db.add(u); db.flush()
    if data.role in ("delegate", "president"):
        db.add(Delegate(user_id=u.id, portfolio=data.portfolio, categories_handled=data.categories_handled,
                        max_open_load=data.max_open_load))
    services.audit(db, admin, "create_user", "user", u.id); db.commit()
    return {"id": u.id}
