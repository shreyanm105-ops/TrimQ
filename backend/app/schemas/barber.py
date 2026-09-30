from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# BARBER SHOP CREATE / UPDATE
# =========================================================

class ShopCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    official_name: Optional[str] = None
    tagline: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    about_shop: Optional[str] = None
    amenities: Optional[str] = None
    opening_time: str = "09:00"
    closing_time: str = "21:00"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shop_logo: Optional[str] = None
    shop_cover: Optional[str] = None
    profile_status: Optional[str] = "draft"
    shop_slug: Optional[str] = None
    service_start_price: Optional[int] = 0
    experience_years: Optional[int] = 0


# =========================================================
# BARBER SHOP RESPONSE
# =========================================================

class ShopResponse(ShopCreate):
    id: int
    owner_id: int

    class Config:
        from_attributes = True


class WalkInCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = None