from math import atan2, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import (
    User,
    Shop,
    Service,
    Booking,
    QueueEntry,
    Notification,
    BarberProfile,
    FavoriteBarber,
    Review,
    HairstyleCategory,
    PortfolioItem,
)

from ..schemas.booking import BookingCreate
from ..schemas.marketplace import ReviewCreate


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/customer",
    tags=["Customer"]
)


# =========================================================
# AUTH
# =========================================================

security = HTTPBearer()

SECRET_KEY = "CHANGE_THIS_TRIMQ_SECRET"
ALGORITHM = "HS256"


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get logged-in customer from JWT.
    """

    try:

        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = int(payload["sub"])

    except (JWTError, KeyError, ValueError):

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if user.role != "customer":

        raise HTTPException(
            status_code=403,
            detail="Customer access required",
        )

    return user


def _calculate_distance_km(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    try:
        earth_radius_km = 6371.0
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            sin(dlat / 2) ** 2
            + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return round(earth_radius_km * c, 2)
    except Exception:
        return None


def _shop_payload(shop: Shop, db: Session, distance_km: float | None = None):
    services = db.query(Service).filter(
        Service.shop_id == shop.id,
        Service.is_active == True,
    ).order_by(Service.price.asc()).all()

    review_rows = db.query(Review).filter(Review.shop_id == shop.id).all()
    rating_values = [row.rating for row in review_rows] if review_rows else []
    avg_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 0
    if shop.average_rating and not rating_values:
        avg_rating = round(float(shop.average_rating), 1)

    cheapest_price = min((service.price for service in services), default=0)
    if shop.service_start_price and cheapest_price == 0:
        cheapest_price = int(shop.service_start_price)

    return {
        "id": shop.id,
        "name": shop.name,
        "official_name": shop.official_name or shop.name,
        "tagline": shop.tagline or "Professional grooming & styling care",
        "description": shop.description,
        "about_shop": shop.about_shop,
        "address": shop.address,
        "city": shop.city,
        "state": shop.state,
        "pincode": shop.pincode,
        "phone": shop.phone,
        "opening_time": shop.opening_time,
        "closing_time": shop.closing_time,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "distance_km": distance_km,
        "shop_logo": shop.shop_logo,
        "shop_cover": shop.shop_cover,
        "owner_id": shop.owner_id,
        "shop_slug": shop.shop_slug,
        "amenities": shop.amenities,
        "verification_status": shop.verification_status,
        "profile_status": shop.profile_status or "draft",
        "is_verified": bool(shop.is_verified),
        "average_rating": avg_rating,
        "rating_count": len(rating_values),
        "experience_years": shop.experience_years or 0,
        "service_start_price": cheapest_price,
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "category": service.category,
                "price": service.price,
                "duration_minutes": service.duration_minutes,
                "is_active": service.is_active,
            }
            for service in services
        ],
    }


# =========================================================
# CUSTOMER PROFILE
# =========================================================

@router.get("/profile")
def get_customer_profile(
    customer=Depends(get_current_customer),
):
    """
    Get logged-in customer profile.
    """

    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "role": customer.role,
        "is_active": customer.is_active,
    }


# =========================================================
# UPDATE CUSTOMER PROFILE
# =========================================================

@router.put("/profile")
def update_customer_profile(
    name: str | None = None,
    phone: str | None = None,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Customer can update own profile.
    """

    if name is not None:
        customer.name = name

    if phone is not None:
        customer.phone = phone

    db.commit()
    db.refresh(customer)

    return {
        "message": "Profile updated successfully",
        "profile": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "role": customer.role,
        },
    }


# =========================================================
# GET ALL BARBER SHOPS
# =========================================================

@router.get("/shops")
def get_all_shops(
    db: Session = Depends(get_db),
    latitude: float | None = None,
    longitude: float | None = None,
    sort: str = "nearby",
):
    """
    Public barber/shop list with distance, price, and experience sorting.
    """

    shops = db.query(Shop).order_by(Shop.id.desc()).all()
    result = []

    for shop in shops:
        distance = None
        if latitude is not None and longitude is not None and shop.latitude is not None and shop.longitude is not None:
            distance = _calculate_distance_km(latitude, longitude, shop.latitude, shop.longitude)
        result.append(_shop_payload(shop, db, distance_km=distance))

    if sort == "cheapest":
        result.sort(key=lambda item: (item.get("service_start_price") or 999999, item.get("distance_km") or 999999))
    elif sort == "experienced":
        result.sort(key=lambda item: (-(item.get("experience_years") or 0), item.get("distance_km") or 999999))
    elif sort == "rating":
        result.sort(key=lambda item: (-(item.get("average_rating") or 0), -(item.get("rating_count") or 0)))
    else:
        result.sort(key=lambda item: (item.get("distance_km") is None, item.get("distance_km") or 999999))

    return result


# =========================================================
# GET SINGLE SHOP
# =========================================================

@router.get("/shops/{shop_id}")
def get_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    latitude: float | None = None,
    longitude: float | None = None,
):
    """
    Customer can view one barber's online shop.
    """

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:

        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    distance = None
    if latitude is not None and longitude is not None and shop.latitude is not None and shop.longitude is not None:
        distance = _calculate_distance_km(latitude, longitude, shop.latitude, shop.longitude)

    return _shop_payload(shop, db, distance_km=distance)


@router.get("/shops/{shop_id}/public-profile")
def get_shop_public_profile(
    shop_id: int,
    db: Session = Depends(get_db),
    latitude: float | None = None,
    longitude: float | None = None,
):
    return get_shop(shop_id=shop_id, db=db, latitude=latitude, longitude=longitude)


# =========================================================
# GET SHOP SERVICES
# =========================================================

@router.get("/shops/{shop_id}/services")
def get_shop_services(
    shop_id: int,
    db: Session = Depends(get_db),
):
    """
    Return only active services belonging
    to the selected barber shop.
    """

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:

        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    services = db.query(Service).filter(
        Service.shop_id == shop_id,
        Service.is_active == True,
    ).order_by(
        Service.id
    ).all()

    return services


# =========================================================
# AVAILABLE SLOTS
# =========================================================

@router.get("/shops/{shop_id}/slots")
def get_available_slots(
    shop_id: int,
    booking_date: str,
    db: Session = Depends(get_db),
):
    """
    Get available 30-minute slots.

    Already booked slots are removed.
    """

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:

        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    # -----------------------------------------------------
    # Existing bookings
    # -----------------------------------------------------

    booked_rows = db.query(
        Booking.slot_time
    ).filter(
        Booking.shop_id == shop_id,
        Booking.booking_date == booking_date,
        Booking.status.notin_(
            ["cancelled"]
        ),
    ).all()

    booked_slots = {
        row.slot_time
        for row in booked_rows
    }

    # -----------------------------------------------------
    # Generate slots
    # -----------------------------------------------------

    try:

        opening_hour = int(
            shop.opening_time.split(":")[0]
        )

        opening_minute = int(
            shop.opening_time.split(":")[1]
        )

        closing_hour = int(
            shop.closing_time.split(":")[0]
        )

        closing_minute = int(
            shop.closing_time.split(":")[1]
        )

    except Exception:

        opening_hour = 9
        opening_minute = 0

        closing_hour = 21
        closing_minute = 0

    available_slots = []

    current_minutes = (
        opening_hour * 60
        + opening_minute
    )

    closing_minutes = (
        closing_hour * 60
        + closing_minute
    )

    while current_minutes < closing_minutes:

        hour = current_minutes // 60
        minute = current_minutes % 60

        slot = f"{hour:02d}:{minute:02d}"

        if slot not in booked_slots:

            available_slots.append(slot)

        current_minutes += 30

    return {
        "shop_id": shop_id,
        "date": booking_date,
        "available_slots": available_slots,
    }


# =========================================================
# CREATE BOOKING
# =========================================================

@router.post("/bookings")
def create_booking(
    data: BookingCreate,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Create customer booking.

    IMPORTANT:
    Same shop + same date + same slot
    cannot be booked twice.
    """

    # -----------------------------------------------------
    # Check shop
    # -----------------------------------------------------

    shop = db.query(Shop).filter(
        Shop.id == data.shop_id
    ).first()

    if not shop:

        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    # -----------------------------------------------------
    # Check service
    # -----------------------------------------------------

    service = db.query(Service).filter(
        Service.id == data.service_id,
        Service.shop_id == data.shop_id,
        Service.is_active == True,
    ).first()

    if not service:

        raise HTTPException(
            status_code=400,
            detail="Invalid service for this shop",
        )

    # -----------------------------------------------------
    # Check slot
    # -----------------------------------------------------

    existing_booking = db.query(
        Booking
    ).filter(
        Booking.shop_id == data.shop_id,
        Booking.booking_date == data.booking_date,
        Booking.slot_time == data.slot_time,
        Booking.status.notin_(
            ["cancelled"]
        ),
    ).first()

    if existing_booking:

        raise HTTPException(
            status_code=409,
            detail="This slot is already booked",
        )

    # -----------------------------------------------------
    # Create booking
    # -----------------------------------------------------

    booking = Booking(
        shop_id=data.shop_id,
        customer_id=customer.id,
        service_id=data.service_id,
        booking_date=data.booking_date,
        slot_time=data.slot_time,
        status="booked",
    )

    db.add(booking)

    # -----------------------------------------------------
    # Flush to get booking ID
    # -----------------------------------------------------

    try:

        db.flush()

        # -------------------------------------------------
        # Calculate queue position
        # -------------------------------------------------

        last_queue = db.query(
            QueueEntry
        ).filter(
            QueueEntry.shop_id == shop.id,
            QueueEntry.status.in_(
                ["waiting", "serving"]
            ),
        ).order_by(
            QueueEntry.position.desc()
        ).first()

        if last_queue:

            next_position = (
                last_queue.position + 1
            )

        else:

            next_position = 1

        # -------------------------------------------------
        # Add queue
        # -------------------------------------------------

        queue_entry = QueueEntry(
            shop_id=shop.id,
            booking_id=booking.id,
            customer_id=customer.id,
            position=next_position,
            status="waiting",
        )

        db.add(queue_entry)

        # -------------------------------------------------
        # Booking notification
        # -------------------------------------------------

        notification = Notification(
            user_id=customer.id,
            title="Booking Confirmed",
            message=(
                f"Your booking at {shop.name} "
                f"for {data.booking_date} "
                f"at {data.slot_time} "
                f"has been confirmed."
            ),
        )

        db.add(notification)

        # -------------------------------------------------
        # Notify barber
        # -------------------------------------------------

        barber_notification = Notification(
            user_id=shop.owner_id,
            title="New Booking",
            message=(
                f"{customer.name} booked "
                f"{data.booking_date} "
                f"at {data.slot_time}."
            ),
        )

        db.add(barber_notification)

        db.commit()

        db.refresh(booking)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Unable to book this slot. "
                "It may have just been booked "
                "by another customer."
            ),
        )

    return {
        "message": "Booking created successfully",
        "booking": {
            "id": booking.id,
            "shop_id": booking.shop_id,
            "customer_id": booking.customer_id,
            "service_id": booking.service_id,
            "booking_date": booking.booking_date,
            "slot_time": booking.slot_time,
            "status": booking.status,
        },
    }


# =========================================================
# MY BOOKINGS
# =========================================================

@router.get("/bookings")
def get_my_bookings(
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Customer's bookings.
    """

    bookings = db.query(
        Booking
    ).filter(
        Booking.customer_id == customer.id
    ).order_by(
        Booking.booking_date.desc(),
        Booking.slot_time.desc()
    ).all()

    result = []

    for booking in bookings:

        shop = db.query(Shop).filter(
            Shop.id == booking.shop_id
        ).first()

        service = db.query(Service).filter(
            Service.id == booking.service_id
        ).first()

        result.append({
            "id": booking.id,
            "shop_id": booking.shop_id,
            "shop_name": (
                shop.name
                if shop
                else "Unknown Shop"
            ),
            "service_id": booking.service_id,
            "service_name": (
                service.name
                if service
                else "Unknown Service"
            ),
            "booking_date": booking.booking_date,
            "slot_time": booking.slot_time,
            "status": booking.status,
            "created_at": booking.created_at,
        })

    return result


# =========================================================
# CANCEL BOOKING
# =========================================================

@router.patch(
    "/bookings/{booking_id}/cancel"
)
def cancel_booking(
    booking_id: int,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Customer can cancel own booking.
    """

    booking = db.query(
        Booking
    ).filter(
        Booking.id == booking_id,
        Booking.customer_id == customer.id,
    ).first()

    if not booking:

        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if booking.status == "completed":

        raise HTTPException(
            status_code=400,
            detail="Completed booking cannot be cancelled",
        )

    booking.status = "cancelled"

    # -----------------------------------------------------
    # Remove from active queue
    # -----------------------------------------------------

    queue_entry = db.query(
        QueueEntry
    ).filter(
        QueueEntry.booking_id == booking.id
    ).first()

    if queue_entry:

        queue_entry.status = "cancelled"

    # -----------------------------------------------------
    # Notify barber
    # -----------------------------------------------------

    shop = db.query(
        Shop
    ).filter(
        Shop.id == booking.shop_id
    ).first()

    if shop:

        db.add(
            Notification(
                user_id=shop.owner_id,
                title="Booking Cancelled",
                message=(
                    f"{customer.name} cancelled "
                    f"the booking for "
                    f"{booking.booking_date} "
                    f"at {booking.slot_time}."
                ),
            )
        )

    db.commit()

    return {
        "message": "Booking cancelled successfully"
    }


# =========================================================
# LIVE QUEUE
# =========================================================

@router.get("/queue/{shop_id}")
def get_live_queue(
    shop_id: int,
    db: Session = Depends(get_db),
):
    """
    Public live queue for a barber shop.
    """

    shop = db.query(Shop).filter(
        Shop.id == shop_id
    ).first()

    if not shop:

        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    rows = (
        db.query(
            QueueEntry,
            User,
        )
        .join(
            User,
            User.id == QueueEntry.customer_id,
        )
        .filter(
            QueueEntry.shop_id == shop_id,
            QueueEntry.status.in_(
                ["waiting", "serving"]
            ),
        )
        .order_by(
            QueueEntry.position
        )
        .all()
    )

    result = []

    for queue_entry, customer in rows:

        result.append({
            "position": queue_entry.position,
            "customer": customer.name,
            "status": queue_entry.status,
        })

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "queue": result,
    }


# =========================================================
# MY NOTIFICATIONS
# =========================================================

@router.get("/notifications")
def get_notifications(
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Get customer's notifications.
    """

    notifications = db.query(
        Notification
    ).filter(
        Notification.user_id == customer.id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return notifications


# =========================================================
# MARK NOTIFICATION AS READ
# =========================================================

@router.patch(
    "/notifications/{notification_id}/read"
)
def mark_notification_read(
    notification_id: int,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Mark own notification as read.
    """

    notification = db.query(
        Notification
    ).filter(
        Notification.id == notification_id,
        Notification.user_id == customer.id,
    ).first()

    if not notification:

        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.is_read = True

    db.commit()

    return {
        "message": "Notification marked as read"
    }


# =========================================================
# DISCOVERY / PUBLIC PROFILES
# =========================================================

@router.get("/discovery")
def get_barber_discovery(
    search: str | None = None,
    city: str | None = None,
    service: str | None = None,
    max_price: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Shop)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            (Shop.name.ilike(f"%{search}%")) |
            (Shop.address.ilike(f"%{search}%")) |
            (Shop.description.ilike(f"%{search}%"))
        )

    if city:
        query = query.filter(Shop.city.ilike(f"%{city}%"))

    shops = query.order_by(Shop.id.desc()).all()

    results = []
    for shop in shops:
        services = db.query(Service).filter(
            Service.shop_id == shop.id,
            Service.is_active == True,
        ).all()

        if service:
            services = [item for item in services if service.lower() in (item.name.lower() or "") or service.lower() in (item.category.lower() if item.category else "")]
            if not services:
                continue

        if max_price is not None:
            services = [item for item in services if item.price <= max_price]
            if not services:
                continue

        barber = db.query(User).filter(User.id == shop.owner_id).first()
        profile = db.query(BarberProfile).filter(BarberProfile.barber_id == shop.owner_id).first()
        avg_rating = db.query(Review.rating).filter(Review.shop_id == shop.id).with_entities(Review.rating).all()
        rating_values = [row[0] for row in avg_rating]
        average_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 0.0
        queue_waiting = db.query(QueueEntry).filter(QueueEntry.shop_id == shop.id, QueueEntry.status.in_(["waiting", "serving"])).count()

        distance_km = None
        if latitude is not None and longitude is not None and shop.latitude is not None and shop.longitude is not None:
            distance_km = round(
                _calculate_distance_km(latitude, longitude, shop.latitude, shop.longitude),
                2,
            )

        results.append({
            "shop_id": shop.id,
            "barber_id": shop.owner_id,
            "barber_name": barber.name if barber else "Barber",
            "shop_name": shop.name,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "distance_km": distance_km,
            "rating": average_rating,
            "review_count": len(rating_values),
            "verified": bool(profile and profile.is_verified),
            "queue_waiting": queue_waiting,
            "opening_time": shop.opening_time,
            "closing_time": shop.closing_time,
            "service_count": len(services),
            "starting_price": min((item.price for item in services), default=0),
            "profile_photo": profile.profile_photo if profile else None,
            "shop_logo": shop.shop_logo,
            "shop_cover": shop.shop_cover,
            "about_shop": shop.about_shop,
        })

    return results


@router.get("/nearby")
def get_nearby_barbers(
    latitude: float | None = None,
    longitude: float | None = None,
    db: Session = Depends(get_db),
):
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required")

    shops = db.query(Shop).filter(Shop.latitude.is_not(None), Shop.longitude.is_not(None)).all()
    results = []
    for shop in shops:
        distance_km = _calculate_distance_km(latitude, longitude, shop.latitude, shop.longitude)
        if distance_km > 25:
            continue
        barber = db.query(User).filter(User.id == shop.owner_id).first()
        profile = db.query(BarberProfile).filter(BarberProfile.barber_id == shop.owner_id).first()
        services = db.query(Service).filter(Service.shop_id == shop.id, Service.is_active == True).all()
        results.append({
            "shop_id": shop.id,
            "barber_id": shop.owner_id,
            "barber_name": barber.name if barber else "Barber",
            "shop_name": shop.name,
            "distance_km": round(distance_km, 2),
            "estimated_travel_minutes": int(distance_km * 6) if distance_km > 0 else 0,
            "queue_waiting": db.query(QueueEntry).filter(QueueEntry.shop_id == shop.id, QueueEntry.status.in_(["waiting", "serving"])).count(),
            "starting_price": min((item.price for item in services), default=0),
            "verified": bool(profile and profile.is_verified),
            "city": shop.city,
            "address": shop.address,
        })

    return sorted(results, key=lambda item: item["distance_km"])


@router.get("/shops/{shop_id}/public-profile")
def get_public_barber_profile(
    shop_id: int,
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    barber = db.query(User).filter(User.id == shop.owner_id).first()
    profile = db.query(BarberProfile).filter(BarberProfile.barber_id == shop.owner_id).first()
    services = db.query(Service).filter(Service.shop_id == shop.id, Service.is_active == True).order_by(Service.price).all()
    portfolio = db.query(PortfolioItem).filter(PortfolioItem.shop_id == shop.id).order_by(PortfolioItem.id.desc()).all()
    review_rows = db.query(Review).filter(Review.shop_id == shop.id).all()
    average_rating = round(sum(item.rating for item in review_rows) / len(review_rows), 1) if review_rows else 0.0
    queue_waiting = db.query(QueueEntry).filter(QueueEntry.shop_id == shop.id, QueueEntry.status.in_(["waiting", "serving"])).count()

    return {
        "barber_name": barber.name if barber else "Barber",
        "profile_photo": profile.profile_photo if profile else None,
        "verified": bool(profile and profile.is_verified),
        "experience_years": profile.experience_years if profile else 0,
        "shop_name": shop.name,
        "address": shop.address,
        "city": shop.city,
        "state": shop.state,
        "phone": shop.phone,
        "opening_time": shop.opening_time,
        "closing_time": shop.closing_time,
        "about_shop": shop.about_shop or shop.description,
        "bio": profile.bio if profile else None,
        "services": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "duration_minutes": item.duration_minutes,
                "category": item.category,
            }
            for item in services
        ],
        "portfolio": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "price": item.price,
                "image_url": item.image_url,
            }
            for item in portfolio
        ],
        "average_rating": average_rating,
        "review_count": len(review_rows),
        "queue_waiting": queue_waiting,
        "shop_logo": shop.shop_logo,
        "shop_cover": shop.shop_cover,
    }


@router.get("/hairstyles")
def get_hairstyle_categories(db: Session = Depends(get_db)):
    categories = db.query(HairstyleCategory).filter(HairstyleCategory.active == True).order_by(HairstyleCategory.id).all()
    if not categories:
        categories = [
            HairstyleCategory(name="Fade", slug="fade", description="Modern fade and sharp outline.", image_url="", price_range="₹400-₹1200", active=True),
            HairstyleCategory(name="Taper", slug="taper", description="Classic taper for clean, professional finish.", image_url="", price_range="₹350-₹900", active=True),
            HairstyleCategory(name="Buzz Cut", slug="buzz-cut", description="Low maintenance short trim.", image_url="", price_range="₹250-₹600", active=True),
            HairstyleCategory(name="Crew Cut", slug="crew-cut", description="Structured short haircut.", image_url="", price_range="₹300-₹700", active=True),
            HairstyleCategory(name="Long Hair", slug="long-hair", description="Styles and finishing for longer hair.", image_url="", price_range="₹500-₹1500", active=True),
        ]
        for item in categories:
            db.add(item)
        db.commit()

    return [
        {"id": item.id, "name": item.name, "slug": item.slug, "description": item.description, "image_url": item.image_url, "price_range": item.price_range}
        for item in categories
    ]


@router.get("/favorites")
def get_favorites(
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    favorites = db.query(FavoriteBarber).filter(FavoriteBarber.customer_id == customer.id).order_by(FavoriteBarber.created_at.desc()).all()
    result = []
    for item in favorites:
        shop = db.query(Shop).filter(Shop.id == item.shop_id).first()
        barber = db.query(User).filter(User.id == shop.owner_id).first() if shop else None
        result.append({
            "id": item.id,
            "shop_id": item.shop_id,
            "shop_name": shop.name if shop else "Shop",
            "barber_name": barber.name if barber else "Barber",
            "address": shop.address if shop else None,
            "city": shop.city if shop else None,
        })
    return result


@router.post("/favorites/{shop_id}")
def add_favorite(
    shop_id: int,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    existing = db.query(FavoriteBarber).filter(FavoriteBarber.customer_id == customer.id, FavoriteBarber.shop_id == shop_id).first()
    if existing:
        return {"message": "Already in favorites"}

    favorite = FavoriteBarber(customer_id=customer.id, shop_id=shop_id)
    db.add(favorite)
    db.commit()
    return {"message": "Favorite added successfully"}


@router.delete("/favorites/{shop_id}")
def remove_favorite(
    shop_id: int,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    favorite = db.query(FavoriteBarber).filter(FavoriteBarber.customer_id == customer.id, FavoriteBarber.shop_id == shop_id).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(favorite)
    db.commit()
    return {"message": "Favorite removed successfully"}


@router.get("/reviews/{shop_id}")
def get_shop_reviews(
    shop_id: int,
    db: Session = Depends(get_db),
):
    reviews = db.query(Review).filter(Review.shop_id == shop_id).order_by(Review.created_at.desc()).all()
    result = []
    for review in reviews:
        customer = db.query(User).filter(User.id == review.customer_id).first()
        result.append({
            "id": review.id,
            "customer_name": customer.name if customer else "Customer",
            "rating": review.rating,
            "review": review.review,
            "service_feedback": review.service_feedback,
            "created_at": review.created_at,
        })
    return result


@router.post("/reviews")
def create_review(
    data: ReviewCreate,
    customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(Booking.id == data.booking_id, Booking.customer_id == customer.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Only completed bookings can be reviewed")

    existing = db.query(Review).filter(Review.booking_id == data.booking_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="This booking has already been reviewed")

    shop = db.query(Shop).filter(Shop.id == booking.shop_id).first()
    review = Review(
        booking_id=data.booking_id,
        shop_id=booking.shop_id,
        barber_id=shop.owner_id if shop else customer.id,
        customer_id=customer.id,
        rating=data.rating,
        review=data.review,
        service_feedback=data.service_feedback,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"message": "Review submitted successfully", "review": review}


def _calculate_distance_km(lat1, lon1, lat2, lon2):
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius_km * c
