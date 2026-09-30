from pydantic import BaseModel


# =========================================================
# CREATE BOOKING
# =========================================================

class BookingCreate(BaseModel):

    shop_id: int

    service_id: int

    booking_date: str

    slot_time: str


# =========================================================
# BOOKING RESPONSE
# =========================================================

class BookingResponse(BaseModel):

    id: int

    shop_id: int

    customer_id: int

    service_id: int

    booking_date: str

    slot_time: str

    status: str

    class Config:
        from_attributes = True