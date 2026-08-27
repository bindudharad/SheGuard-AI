from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import LoginRequest, RegisterRequest
from backend.database import get_db
from backend.models import User
from backend.services.security import create_access_token, hash_password, verify_password


router = APIRouter(tags=["users"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")
    user = User(
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        profile_photo=payload.profile_photo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.user_id, "full_name": user.full_name, "phone_number": user.phone_number}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    token = create_access_token(str(user.user_id))
    return {
        "status": "ok",
        "user_id": user.user_id,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/profile/{user_id}")
def profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "profile_photo": user.profile_photo,
        "created_at": user.created_at,
    }
