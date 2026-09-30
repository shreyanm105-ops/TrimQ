import re
import secrets

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
    PortfolioItem,
    VerificationDocument,
)

from ..schemas.barber import ShopCreate, WalkInCreate
from ..schemas.marketplace import (
    ProfessionalProfileUpdate,
    ShopProfileUpdate,
    PortfolioItemCreate,
    VerificationDocumentCreate,
)
from ..schemas.service import ServiceCreate


router = APIRouter(
    prefix="/api/barber",
    tags=["Barber"]
)

security = HTTPBearer()

SECRET_KEY = "CHANGE_THIS_TRIMQ_SECRET"
ALGORITHM = "HS256"


def _make_shop_slug(name: str, db: Session, current_id: int | None = None) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "trimq-shop").lower()).strip("-")
    slug = base or "trimq-shop"
    final_slug = slug[:80]
    counter = 2

    while True:
        existing = db.query(Shop).filter(Shop.shop_slug == final_slug).first()
        if not existing or existing.id == current_id:
            return final_slug
        final_slug = f"{slug[:72]}-{counter}"
        counter += 1


# =========================================================
# AUTH
# =========================================================

def get_current_barber(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
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

    if user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Barber access required",
        )

    return user


# =========================================================
# BARBER PROFILE
# =========================================================

@router.get("/profile")
def get_barber_profile(
    barber=Depends(get_current_barber),
):
    return {
        "id": barber.id,
        "name": barber.name,
        "email": barber.email,
        "phone": barber.phone,
        "role": barber.role,
        "is_active": barber.is_active,
    }


@router.put("/profile")
def update_barber_profile(
    name: str | None = None,
    phone: str | None = None,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    if name is not None:
        barber.name = name.strip()

    if phone is not None:
        barber.phone = phone

    db.commit()
    db.refresh(barber)

    return {
        "message": "Barber profile updated successfully",
        "profile": {
            "id": barber.id,
            "name": barber.name,
            "email": barber.email,
            "phone": barber.phone,
            "role": barber.role,
        },
    }


# =========================================================
# SHOP
# =========================================================

@router.get("/shop")
def get_my_shop(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    return shop


@router.post("/shop")
def create_my_shop(
    data: ShopCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    existing_shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if existing_shop:
        raise HTTPException(
            status_code=400,
            detail="You already have a shop",
        )

    if not data.name or not data.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Shop name is required",
        )

    if not data.address or not data.address.strip():
        raise HTTPException(
            status_code=400,
            detail="Shop address is required",
        )

    if not data.phone or not data.phone.strip():
        raise HTTPException(
            status_code=400,
            detail="Shop phone is required",
        )

    shop = Shop(
        owner_id=barber.id,
        name=data.name.strip(),
        official_name=(data.official_name or data.name).strip(),
        tagline=(data.tagline or "Professional grooming and style care").strip(),
        address=data.address.strip(),
        city=(data.city or "").strip() or None,
        state=(data.state or "").strip() or None,
        pincode=(data.pincode or "").strip() or None,
        phone=data.phone.strip(),
        description=data.description.strip() if data.description else None,
        about_shop=data.about_shop.strip() if data.about_shop else None,
        amenities=data.amenities.strip() if data.amenities else None,
        opening_time=data.opening_time,
        closing_time=data.closing_time,
        latitude=data.latitude,
        longitude=data.longitude,
        shop_logo=data.shop_logo,
        shop_cover=data.shop_cover,
        profile_status=data.profile_status or "draft",
        service_start_price=int(data.service_start_price or 0),
        experience_years=int(data.experience_years or 0),
        verification_status="pending",
        shop_slug=_make_shop_slug(data.name, db),
    )

    db.add(shop)
    db.commit()
    db.refresh(shop)

    return shop


@router.put("/shop")
def update_my_shop(
    data: ShopCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    if data.name and data.name.strip():
        shop.name = data.name.strip()
        shop.official_name = (data.official_name or data.name).strip()
        shop.shop_slug = _make_shop_slug(data.name, db, current_id=shop.id)

    if data.address is not None:
        shop.address = data.address.strip() or None
    if data.phone is not None:
        shop.phone = data.phone.strip() or None
    if data.description is not None:
        shop.description = data.description.strip() or None
    if data.about_shop is not None:
        shop.about_shop = data.about_shop.strip() or None
    if data.amenities is not None:
        shop.amenities = data.amenities.strip() or None
    if data.city is not None:
        shop.city = data.city.strip() or None
    if data.state is not None:
        shop.state = data.state.strip() or None
    if data.pincode is not None:
        shop.pincode = data.pincode.strip() or None
    if data.latitude is not None:
        shop.latitude = data.latitude
    if data.longitude is not None:
        shop.longitude = data.longitude
    if data.tagline is not None:
        shop.tagline = data.tagline.strip() or None
    if data.shop_logo is not None:
        shop.shop_logo = data.shop_logo
    if data.shop_cover is not None:
        shop.shop_cover = data.shop_cover
    if data.profile_status is not None:
        shop.profile_status = data.profile_status
    if data.service_start_price is not None:
        shop.service_start_price = int(data.service_start_price)
    if data.experience_years is not None:
        shop.experience_years = int(data.experience_years)

    shop.opening_time = data.opening_time or shop.opening_time
    shop.closing_time = data.closing_time or shop.closing_time

    db.commit()
    db.refresh(shop)

    return shop


@router.get("/shop/public")
def get_public_shop_summary(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    services = db.query(Service).filter(Service.shop_id == shop.id, Service.is_active == True).all()
    average_price = round(sum(item.price for item in services) / len(services), 2) if services else 0

    return {
        "id": shop.id,
        "name": shop.name,
        "official_name": shop.official_name or shop.name,
        "tagline": shop.tagline,
        "address": shop.address,
        "city": shop.city,
        "state": shop.state,
        "pincode": shop.pincode,
        "phone": shop.phone,
        "description": shop.description,
        "about_shop": shop.about_shop,
        "amenities": shop.amenities,
        "opening_time": shop.opening_time,
        "closing_time": shop.closing_time,
        "shop_slug": shop.shop_slug,
        "profile_status": shop.profile_status,
        "is_verified": shop.is_verified,
        "average_rating": shop.average_rating,
        "rating_count": shop.rating_count,
        "experience_years": shop.experience_years,
        "service_start_price": shop.service_start_price,
        "average_service_price": average_price,
        "services": services,
    }


# =========================================================
# SERVICES
# =========================================================

@router.get("/services")
def get_my_services(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    return db.query(Service).filter(
        Service.shop_id == shop.id
    ).order_by(
        Service.id.desc()
    ).all()


@router.post("/services")
def create_service(
    data: ServiceCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    service = Service(
        shop_id=shop.id,
        name=data.name,
        description=data.description,
        price=data.price,
        duration_minutes=data.duration_minutes,
        is_active=data.is_active,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service


@router.put("/services/{service_id}")
def update_service(
    service_id: int,
    data: ServiceCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.shop_id == shop.id,
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    service.name = data.name
    service.description = data.description
    service.price = data.price
    service.duration_minutes = data.duration_minutes
    service.is_active = data.is_active

    db.commit()
    db.refresh(service)

    return service


@router.delete("/services/{service_id}")
def deactivate_service(
    service_id: int,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.shop_id == shop.id,
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    service.is_active = False

    db.commit()

    return {
        "message": "Service deactivated successfully"
    }


# =========================================================
# CUSTOMERS
# =========================================================

@router.get("/customers")
def get_my_customers(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    customers = (
        db.query(User)
        .join(
            Booking,
            Booking.customer_id == User.id
        )
        .filter(
            Booking.shop_id == shop.id
        )
        .distinct()
        .all()
    )

    return [
        {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
        }
        for customer in customers
    ]


# =========================================================
# APPOINTMENTS
# =========================================================

@router.get("/appointments")
def get_my_appointments(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    bookings = db.query(Booking).filter(
        Booking.shop_id == shop.id
    ).order_by(
        Booking.booking_date,
        Booking.slot_time
    ).all()

    result = []

    for booking in bookings:
        customer = db.query(User).filter(
            User.id == booking.customer_id
        ).first()

        service = db.query(Service).filter(
            Service.id == booking.service_id
        ).first()

        result.append({
            "id": booking.id,
            "customer_id": booking.customer_id,
            "customer_name": (
                customer.name
                if customer else "Unknown"
            ),
            "service_id": booking.service_id,
            "service_name": (
                service.name
                if service else "Unknown"
            ),
            "booking_date": booking.booking_date,
            "slot_time": booking.slot_time,
            "status": booking.status,
        })

    return result


# =========================================================
# BOOKING STATUS
# =========================================================

@router.patch("/bookings/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    status: str,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    allowed_statuses = [
        "booked",
        "confirmed",
        "serving",
        "completed",
        "cancelled",
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {allowed_statuses}",
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.shop_id == shop.id,
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    booking.status = status

    db.add(
        Notification(
            user_id=booking.customer_id,
            title="Booking Updated",
            message=(
                f"Your booking on "
                f"{booking.booking_date} at "
                f"{booking.slot_time} is now "
                f"{status}."
            ),
        )
    )

    db.commit()

    return {
        "message": "Booking status updated",
        "booking_id": booking.id,
        "status": booking.status,
    }


# =========================================================
# QUEUE
# =========================================================

@router.get("/queue")
def get_my_queue(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
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
            QueueEntry.shop_id == shop.id,
            QueueEntry.status.in_( ["waiting", "serving"] ),
        )
        .order_by(
            QueueEntry.position
        )
        .all()
    )

    return [
        {
            "id": queue.id,
            "position": queue.position,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "status": queue.status,
            "booking_id": queue.booking_id,
        }
        for queue, customer in rows
    ]


@router.post("/queue/walk-in")
def add_walk_in(
    data: WalkInCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Create your shop before adding walk-ins",
        )

    name = data.name.strip()
    if not name:
        raise HTTPException(
            status_code=422,
            detail="Customer name is required",
        )

    last_entry = db.query(QueueEntry).filter(
        QueueEntry.shop_id == shop.id,
        QueueEntry.status.in_(["waiting", "serving"]),
    ).order_by(
        QueueEntry.position.desc()
    ).first()
    next_position = last_entry.position + 1 if last_entry else 1

    walk_in_customer = User(
        name=name,
        email=f"walkin-{secrets.token_hex(12)}@trimq.local",
        phone=data.phone.strip() if data.phone and data.phone.strip() else None,
        password=secrets.token_urlsafe(32),
        role="customer",
        is_active=True,
    )
    db.add(walk_in_customer)

    try:
        db.flush()
        queue_entry = QueueEntry(
            shop_id=shop.id,
            booking_id=None,
            customer_id=walk_in_customer.id,
            position=next_position,
            status="waiting",
        )
        db.add(queue_entry)
        db.commit()
        db.refresh(queue_entry)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to add walk-in customer",
        ) from error

    return {
        "id": queue_entry.id,
        "position": queue_entry.position,
        "customer_id": walk_in_customer.id,
        "customer_name": walk_in_customer.name,
        "status": queue_entry.status,
        "booking_id": None,
    }


@router.patch("/queue/{queue_id}/status")
def update_queue_status(
    queue_id: int,
    status: str,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    allowed_statuses = [
        "waiting",
        "serving",
        "completed",
        "cancelled",
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {allowed_statuses}",
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == barber.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found",
        )

    queue = db.query(QueueEntry).filter(
        QueueEntry.id == queue_id,
        QueueEntry.shop_id == shop.id,
    ).first()

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Queue entry not found",
        )

    queue.status = status

    if queue.booking_id:
        booking = db.query(Booking).filter(
            Booking.id == queue.booking_id
        ).first()

        if booking:
            if status == "serving":
                booking.status = "serving"
            elif status == "completed":
                booking.status = "completed"
            elif status == "cancelled":
                booking.status = "cancelled"

    db.add(
        Notification(
            user_id=queue.customer_id,
            title="Queue Updated",
            message=(
                f"Your queue status is now "
                f"{status}."
            ),
        )
    )

    db.commit()

    return {
        "message": "Queue status updated",
        "queue_id": queue.id,
        "status": queue.status,
    }


# =========================================================
# PROFESSIONAL PROFILE
# =========================================================

@router.get("/profile/advanced")
def get_barber_profile_advanced(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    profile = db.query(BarberProfile).filter(BarberProfile.barber_id == barber.id).first()

    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    return {
        "barber": {
            "id": barber.id,
            "name": barber.name,
            "email": barber.email,
            "phone": barber.phone,
            "profile_photo": profile.profile_photo if profile else None,
            "bio": profile.bio if profile else None,
            "experience_years": profile.experience_years if profile else 0,
            "gender": profile.gender if profile else None,
            "languages": profile.languages if profile else None,
            "contact_phone": profile.contact_phone if profile else barber.phone,
            "contact_email": profile.contact_email if profile else barber.email,
            "verification_status": profile.verification_status if profile else "pending",
            "is_verified": bool(profile.is_verified) if profile else False,
        },
        "shop": {
            "id": shop.id,
            "name": shop.name,
            "address": shop.address,
            "city": shop.city,
            "state": shop.state,
            "pincode": shop.pincode,
            "phone": shop.phone,
            "description": shop.description,
            "about_shop": shop.about_shop,
            "opening_time": shop.opening_time,
            "closing_time": shop.closing_time,
            "weekly_holidays": shop.weekly_holidays,
            "latitude": shop.latitude,
            "longitude": shop.longitude,
            "shop_logo": shop.shop_logo,
            "shop_cover": shop.shop_cover,
            "verification_status": shop.verification_status,
        },
    }


@router.put("/profile/advanced")
def update_barber_profile_advanced(
    data: ProfessionalProfileUpdate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    profile = db.query(BarberProfile).filter(BarberProfile.barber_id == barber.id).first()
    if not profile:
        profile = BarberProfile(barber_id=barber.id)
        db.add(profile)

    if data.barber_name is not None:
        barber.name = data.barber_name.strip()
    if data.profile_photo is not None:
        profile.profile_photo = data.profile_photo
    if data.bio is not None:
        profile.bio = data.bio
    if data.experience_years is not None:
        profile.experience_years = data.experience_years
    if data.gender is not None:
        profile.gender = data.gender
    if data.languages is not None:
        profile.languages = data.languages
    if data.contact_phone is not None:
        profile.contact_phone = data.contact_phone
    if data.contact_email is not None:
        profile.contact_email = data.contact_email
    if data.verification_status is not None:
        profile.verification_status = data.verification_status
        profile.is_verified = data.verification_status == "verified"

    db.commit()
    db.refresh(profile)

    return {
        "message": "Professional profile updated successfully",
        "profile": {
            "barber_name": barber.name,
            "profile_photo": profile.profile_photo,
            "bio": profile.bio,
            "experience_years": profile.experience_years,
            "gender": profile.gender,
            "languages": profile.languages,
            "contact_phone": profile.contact_phone,
            "contact_email": profile.contact_email,
            "verification_status": profile.verification_status,
            "is_verified": profile.is_verified,
        },
    }


@router.put("/shop/advanced")
def update_shop_profile_advanced(
    data: ShopProfileUpdate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(shop, field, value)

    if data.name is not None:
        shop.name = data.name.strip()
    if data.phone is not None:
        shop.phone = data.phone
    if data.address is not None:
        shop.address = data.address
    if data.city is not None:
        shop.city = data.city
    if data.state is not None:
        shop.state = data.state
    if data.pincode is not None:
        shop.pincode = data.pincode
    if data.opening_time is not None:
        shop.opening_time = data.opening_time
    if data.closing_time is not None:
        shop.closing_time = data.closing_time
    if data.weekly_holidays is not None:
        shop.weekly_holidays = data.weekly_holidays
    if data.about_shop is not None:
        shop.about_shop = data.about_shop
    if data.latitude is not None:
        shop.latitude = data.latitude
    if data.longitude is not None:
        shop.longitude = data.longitude
    if data.shop_logo is not None:
        shop.shop_logo = data.shop_logo
    if data.shop_cover is not None:
        shop.shop_cover = data.shop_cover

    db.commit()
    db.refresh(shop)
    return shop


# =========================================================
# PORTFOLIO
# =========================================================

@router.get("/portfolio")
def get_portfolio(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    return db.query(PortfolioItem).filter(PortfolioItem.shop_id == shop.id).order_by(PortfolioItem.id.desc()).all()


@router.post("/portfolio")
def create_portfolio_item(
    data: PortfolioItemCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    item = PortfolioItem(
        shop_id=shop.id,
        title=data.title,
        description=data.description,
        category=data.category,
        price=data.price or 0,
        image_url=data.image_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/portfolio/{portfolio_id}")
def update_portfolio_item(
    portfolio_id: int,
    data: PortfolioItemCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id, PortfolioItem.shop_id == shop.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")

    item.title = data.title
    item.description = data.description
    item.category = data.category
    item.price = data.price or 0
    item.image_url = data.image_url
    db.commit()
    db.refresh(item)
    return item


@router.delete("/portfolio/{portfolio_id}")
def delete_portfolio_item(
    portfolio_id: int,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.owner_id == barber.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id, PortfolioItem.shop_id == shop.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")

    db.delete(item)
    db.commit()
    return {"message": "Portfolio item deleted successfully"}


# =========================================================
# VERIFICATION
# =========================================================

@router.get("/verification")
def get_verification_documents(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    docs = db.query(VerificationDocument).filter(VerificationDocument.barber_id == barber.id).order_by(VerificationDocument.uploaded_at.desc()).all()
    result = []
    for doc in docs:
        result.append({
            "id": doc.id,
            "document_type": doc.document_type,
            "document_url": doc.document_url,
            "document_reference": doc.document_reference,
            "masked_reference": doc.masked_reference or "XXXX",
            "status": doc.status,
            "review_notes": doc.review_notes,
            "uploaded_at": doc.uploaded_at,
        })
    return result


@router.post("/verification")
def add_verification_document(
    data: VerificationDocumentCreate,
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    reference = (data.document_reference or "").strip()
    masked = None
    if reference:
        masked = f"XXXX{reference[-4:]}" if len(reference) > 4 else "XXXX"

    document = VerificationDocument(
        barber_id=barber.id,
        document_type=data.document_type,
        document_url=data.document_url,
        document_reference=reference,
        masked_reference=masked,
        status=data.status or "pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/verification-status")
def get_verification_status(
    barber=Depends(get_current_barber),
    db: Session = Depends(get_db),
):
    profile = db.query(BarberProfile).filter(BarberProfile.barber_id == barber.id).first()
    doc = db.query(VerificationDocument).filter(VerificationDocument.barber_id == barber.id).order_by(VerificationDocument.uploaded_at.desc()).first()
    return {
        "status": profile.verification_status if profile else (doc.status if doc else "pending"),
        "is_verified": bool(profile.is_verified) if profile else False,
        "document_uploaded": bool(doc),
    }