from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# =========================================================
# REGISTER
# =========================================================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=100)
    role: str = "customer"


# =========================================================
# LOGIN
# =========================================================

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# =========================================================
# USER RESPONSE
# =========================================================

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# =========================================================
# PROFILE UPDATE
# =========================================================

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=120
    )

    phone: Optional[str] = None


# =========================================================
# LOGIN RESPONSE
# =========================================================

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse