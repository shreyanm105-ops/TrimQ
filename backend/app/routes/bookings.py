from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError

from ..database.database import get_db
from ..database.models import Booking, Shop, Service, User, QueueEntry, Notification

router = APIRouter(
    prefix="/api/bookings",
    tags=["Bookings"]
)

security = HTTPBearer()

SECRET_KEY = "CHANGE_THIS_TRIMQ_SECRET"
ALGORITHM = "HS256"


# =========================================================
# AUTH
# =========================================================

def get_current_user(
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

        user = db.query(User).filter(
            User.id == int(user_id)
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


# =========================================================
# GET ALL BOOKINGS
# =========================================================

@router.get("/")
def get_all_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role == "barber":

        shop = db.query(Shop).filter(
            Shop.owner_id == current_user.id
        ).first()

        if not shop:
            return []

        bookings = db.query(Booking).filter(
            Booking.shop_id == shop.id
        ).order_by(
            Booking.booking_date.asc(),
            Booking.slot_time.asc()
        ).all()

    else:

        bookings = db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(
            Booking.booking_date.asc(),
            Booking.slot_time.asc()
        ).all()

    return bookings


# =========================================================
# GET SINGLE BOOKING
# =========================================================

@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # Customer can see own booking
    if current_user.role == "customer":

        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot access this booking"
            )

    # Barber can see booking of own shop
    elif current_user.role == "barber":

        shop = db.query(Shop).filter(
            Shop.owner_id == current_user.id
        ).first()

        if not shop or booking.shop_id != shop.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot access this booking"
            )

    return booking


# =========================================================
# CANCEL BOOKING
# =========================================================

@router.patch("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only cancel your own booking"
        )

    if booking.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail="Booking cannot be cancelled"
        )

    booking.status = "cancelled"

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.booking_id == booking.id
    ).first()

    if queue_entry:
        queue_entry.status = "cancelled"

    # Notify barber
    shop = db.query(Shop).filter(
        Shop.id == booking.shop_id
    ).first()

    if shop:
        notification = Notification(
            user_id=shop.owner_id,
            title="Booking Cancelled",
            message=(
                f"{current_user.name} cancelled booking "
                f"#{booking.id} for {booking.booking_date} "
                f"at {booking.slot_time}."
            ),
            is_read=False
        )

        db.add(notification)

    db.commit()

    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking.id,
        "status": booking.status
    }


# =========================================================
# BARBER CONFIRM BOOKING
# =========================================================

@router.patch("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can confirm booking"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.shop_id == shop.id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cancelled booking cannot be confirmed"
        )

    booking.status = "confirmed"

    notification = Notification(
        user_id=booking.customer_id,
        title="Booking Confirmed",
        message=(
            f"Your booking at {shop.name} on "
            f"{booking.booking_date} at {booking.slot_time} "
            f"has been confirmed."
        ),
        is_read=False
    )

    db.add(notification)
    db.commit()

    return {
        "message": "Booking confirmed",
        "booking_id": booking.id,
        "status": booking.status
    }


# =========================================================
# BARBER START SERVICE
# =========================================================

@router.patch("/{booking_id}/start")
def start_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can start booking"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.shop_id == shop.id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    booking.status = "serving"

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.booking_id == booking.id
    ).first()

    if queue_entry:
        queue_entry.status = "serving"

    notification = Notification(
        user_id=booking.customer_id,
        title="Your Turn Has Started",
        message=(
            f"Your service at {shop.name} has started."
        ),
        is_read=False
    )

    db.add(notification)
    db.commit()

    return {
        "message": "Booking started",
        "booking_id": booking.id,
        "status": booking.status
    }


# =========================================================
# BARBER COMPLETE BOOKING
# =========================================================

@router.patch("/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can complete booking"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.shop_id == shop.id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    booking.status = "completed"

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.booking_id == booking.id
    ).first()

    if queue_entry:
        queue_entry.status = "completed"

    notification = Notification(
        user_id=booking.customer_id,
        title="Service Completed",
        message=(
            f"Your service at {shop.name} has been completed."
        ),
        is_read=False
    )

    db.add(notification)
    db.commit()

    return {
        "message": "Booking completed",
        "booking_id": booking.id,
        "status": booking.status
    }


# =========================================================
# CHECK SLOT
# =========================================================

@router.get("/check-slot/{shop_id}")
def check_slot(
    shop_id: int,
    booking_date: str,
    slot_time: str,
    db: Session = Depends(get_db)
):

    existing_booking = db.query(Booking).filter(
        Booking.shop_id == shop_id,
        Booking.booking_date == booking_date,
        Booking.slot_time == slot_time,
        Booking.status.notin_(["cancelled", "completed"])
    ).first()

    return {
        "shop_id": shop_id,
        "booking_date": booking_date,
        "slot_time": slot_time,
        "available": existing_booking is None
    }