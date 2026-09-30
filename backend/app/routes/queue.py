from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..database.database import get_db
from ..database.models import (
    QueueEntry,
    Booking,
    Shop,
    User,
    Notification,
)

router = APIRouter(
    prefix="/api/queue",
    tags=["Queue"]
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
# LIVE QUEUE FOR SHOP
# =========================================================

@router.get("/{shop_id}")
def get_live_queue(
    shop_id: int,
    db: Session = Depends(get_db)
):
    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    queue = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop_id,
        QueueEntry.status.in_(["waiting", "serving"])
    ).order_by(
        QueueEntry.position.asc()
    ).all()

    result = []

    for entry in queue:

        customer = db.query(User).filter(
            User.id == entry.customer_id
        ).first()

        booking = None

        if entry.booking_id:
            booking = db.query(Booking).filter(
                Booking.id == entry.booking_id
            ).first()

        result.append({
            "queue_id": entry.id,
            "booking_id": entry.booking_id,
            "customer_id": entry.customer_id,
            "customer_name": (
                customer.name
                if customer
                else "Customer"
            ),
            "position": entry.position,
            "status": entry.status,
            "booking_date": (
                booking.booking_date
                if booking
                else None
            ),
            "slot_time": (
                booking.slot_time
                if booking
                else None
            )
        })

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "total_waiting": len([
            item for item in result
            if item["status"] == "waiting"
        ]),
        "currently_serving": next(
            (
                item
                for item in result
                if item["status"] == "serving"
            ),
            None
        ),
        "queue": result
    }


# =========================================================
# BARBER VIEW OWN QUEUE
# =========================================================

@router.get("/barber/my")
def barber_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can access this endpoint"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    queue = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop.id,
        QueueEntry.status.in_([
            "waiting",
            "serving"
        ])
    ).order_by(
        QueueEntry.position.asc()
    ).all()

    result = []

    for entry in queue:

        customer = db.query(User).filter(
            User.id == entry.customer_id
        ).first()

        result.append({
            "queue_id": entry.id,
            "booking_id": entry.booking_id,
            "customer_id": entry.customer_id,
            "customer_name": (
                customer.name
                if customer
                else "Customer"
            ),
            "position": entry.position,
            "status": entry.status
        })

    return {
        "shop_id": shop.id,
        "shop_name": shop.name,
        "queue": result
    }


# =========================================================
# CUSTOMER OWN QUEUE POSITION
# =========================================================

@router.get("/customer/my")
def customer_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customer can access this endpoint"
        )

    entries = db.query(QueueEntry).filter(
        QueueEntry.customer_id == current_user.id,
        QueueEntry.status.in_([
            "waiting",
            "serving"
        ])
    ).order_by(
        QueueEntry.position.asc()
    ).all()

    result = []

    for entry in entries:

        shop = db.query(Shop).filter(
            Shop.id == entry.shop_id
        ).first()

        result.append({
            "queue_id": entry.id,
            "booking_id": entry.booking_id,
            "shop_id": entry.shop_id,
            "shop_name": (
                shop.name
                if shop
                else "Shop"
            ),
            "position": entry.position,
            "status": entry.status
        })

    return {
        "customer_id": current_user.id,
        "queue": result
    }


# =========================================================
# BARBER START CUSTOMER
# =========================================================

@router.patch("/{queue_id}/start")
def start_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can start queue"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.id == queue_id,
        QueueEntry.shop_id == shop.id
    ).first()

    if not queue_entry:
        raise HTTPException(
            status_code=404,
            detail="Queue entry not found"
        )

    # Only one customer should be serving at a time.
    already_serving = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop.id,
        QueueEntry.status == "serving",
        QueueEntry.id != queue_entry.id
    ).first()

    if already_serving:
        raise HTTPException(
            status_code=409,
            detail="Another customer is already being served"
        )

    queue_entry.status = "serving"

    if queue_entry.booking_id:

        booking = db.query(Booking).filter(
            Booking.id == queue_entry.booking_id
        ).first()

        if booking:
            booking.status = "serving"

    notification = Notification(
        user_id=queue_entry.customer_id,
        title="Your Turn Started",
        message=(
            f"Your turn at {shop.name} has started."
        ),
        is_read=False
    )

    db.add(notification)
    db.commit()

    return {
        "message": "Customer is now being served",
        "queue_id": queue_entry.id,
        "status": queue_entry.status
    }


# =========================================================
# COMPLETE QUEUE ENTRY
# =========================================================

@router.patch("/{queue_id}/complete")
def complete_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can complete queue"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.id == queue_id,
        QueueEntry.shop_id == shop.id
    ).first()

    if not queue_entry:
        raise HTTPException(
            status_code=404,
            detail="Queue entry not found"
        )

    queue_entry.status = "completed"

    if queue_entry.booking_id:

        booking = db.query(Booking).filter(
            Booking.id == queue_entry.booking_id
        ).first()

        if booking:
            booking.status = "completed"

    notification = Notification(
        user_id=queue_entry.customer_id,
        title="Service Completed",
        message=(
            f"Your service at {shop.name} has been completed."
        ),
        is_read=False
    )

    db.add(notification)

    # Notify next waiting customer
    next_customer = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop.id,
        QueueEntry.status == "waiting"
    ).order_by(
        QueueEntry.position.asc()
    ).first()

    if next_customer:

        next_notification = Notification(
            user_id=next_customer.customer_id,
            title="You Are Next",
            message=(
                f"You are next in the queue at {shop.name}."
            ),
            is_read=False
        )

        db.add(next_notification)

    db.commit()

    return {
        "message": "Queue entry completed",
        "queue_id": queue_entry.id,
        "status": queue_entry.status
    }


# =========================================================
# CANCEL QUEUE ENTRY
# =========================================================

@router.patch("/{queue_id}/cancel")
def cancel_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    queue_entry = db.query(QueueEntry).filter(
        QueueEntry.id == queue_id
    ).first()

    if not queue_entry:
        raise HTTPException(
            status_code=404,
            detail="Queue entry not found"
        )

    # Customer can cancel own queue entry
    if current_user.role == "customer":

        if queue_entry.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot cancel this queue entry"
            )

    # Barber can cancel own shop queue entry
    elif current_user.role == "barber":

        shop = db.query(Shop).filter(
            Shop.owner_id == current_user.id
        ).first()

        if not shop or queue_entry.shop_id != shop.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot cancel this queue entry"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    queue_entry.status = "cancelled"

    if queue_entry.booking_id:

        booking = db.query(Booking).filter(
            Booking.id == queue_entry.booking_id
        ).first()

        if booking and booking.status not in [
            "completed",
            "cancelled"
        ]:
            booking.status = "cancelled"

    db.commit()

    return {
        "message": "Queue entry cancelled",
        "queue_id": queue_entry.id,
        "status": queue_entry.status
    }


# =========================================================
# QUEUE SUMMARY
# =========================================================

@router.get("/{shop_id}/summary")
def queue_summary(
    shop_id: int,
    db: Session = Depends(get_db)
):

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    waiting_count = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop_id,
        QueueEntry.status == "waiting"
    ).count()

    serving_count = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop_id,
        QueueEntry.status == "serving"
    ).count()

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "waiting": waiting_count,
        "serving": serving_count,
        "total_active": waiting_count + serving_count
    }