from typing import Optional

from pydantic import BaseModel, Field


class ProfessionalProfileUpdate(BaseModel):
    barber_name: Optional[str] = None
    profile_photo: Optional[str] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = Field(default=None, ge=0)
    gender: Optional[str] = None
    languages: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    verification_status: Optional[str] = None


class ShopProfileUpdate(BaseModel):
    name: Optional[str] = None
    shop_logo: Optional[str] = None
    shop_cover: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    weekly_holidays: Optional[str] = None
    about_shop: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PortfolioItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = Field(default=0, ge=0)
    image_url: str = Field(..., min_length=1, max_length=500)


class VerificationDocumentCreate(BaseModel):
    document_type: str = "aadhaar"
    document_url: str = Field(..., min_length=1, max_length=500)
    document_reference: Optional[str] = None
    status: Optional[str] = "pending"


class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None
    service_feedback: Optional[str] = None


class FavoriteAction(BaseModel):
    shop_id: int
