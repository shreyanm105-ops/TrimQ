from typing import Optional

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    price: int = Field(default=0, ge=0)
    duration_minutes: int = Field(default=30, gt=0)
    is_active: bool = True


class ServiceResponse(ServiceCreate):
    id: int
    shop_id: int

    class Config:
        from_attributes = True