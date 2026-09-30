import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..database.database import get_db
from ..database.models import User
from ..schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    LoginResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

security = HTTPBearer()

SECRET_KEY = os.getenv("TRIMQ_SECRET_KEY", "CHANGE_THIS_TRIMQ_SECRET")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False

    if plain_password == hashed_password:
        return True

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(user_id: int, role: str):
    expire = datetime.utcnow() + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    # Only customer/barber registration allowed
    if user_data.role not in ["customer", "barber"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be customer or barber"
        )

    email = user_data.email.lower().strip()

    # Check duplicate email
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        name=user_data.name.strip(),
        email=email,
        phone=user_data.phone,
        password=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except Exception as e:
        db.rollback()

        print("REGISTER ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail="Unable to create account"
        )

    return user


@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    email = user_data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive"
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user = (
            db.query(User)
            .filter(User.id == int(user_id))
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


@router.post("/logout")
def logout():
    return {
        "message": "Logout successful",
        "note": "Remove the access token from browser storage."
    }