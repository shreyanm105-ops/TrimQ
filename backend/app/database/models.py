from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Text,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="customer", nullable=False)
    is_active = Column(Boolean, default=True)
    gender = Column(String(20), nullable=True)
    profile_photo = Column(String(500), nullable=True)


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    name = Column(String(160), nullable=False)
    address = Column(String(300), nullable=True)
    phone = Column(String(30), nullable=True)
    description = Column(Text, nullable=True)
    official_name = Column(String(200), nullable=True)
    tagline = Column(String(220), nullable=True)
    city = Column(String(120), nullable=True)
    state = Column(String(120), nullable=True)
    pincode = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    shop_logo = Column(String(500), nullable=True)
    shop_cover = Column(String(500), nullable=True)
    weekly_holidays = Column(String(200), nullable=True)
    about_shop = Column(Text, nullable=True)
    amenities = Column(Text, nullable=True)
    verification_status = Column(String(30), default="pending")
    profile_status = Column(String(30), default="draft")
    is_verified = Column(Boolean, default=False)
    average_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    experience_years = Column(Integer, default=0)
    service_start_price = Column(Integer, default=0)
    shop_slug = Column(String(120), unique=True, index=True, nullable=True)

    opening_time = Column(String(10), default="09:00")
    closing_time = Column(String(10), default="21:00")

    owner = relationship("User")


class BarberProfile(Base):
    __tablename__ = "barber_profiles"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    profile_photo = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, default=0)
    gender = Column(String(30), nullable=True)
    languages = Column(String(200), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    contact_email = Column(String(255), nullable=True)
    verification_status = Column(String(30), default="pending")
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)

    shop_id = Column(
        Integer,
        ForeignKey("shops.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(60), default="general")
    price = Column(Integer, nullable=False, default=0)
    duration_minutes = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, default=True)


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(80), nullable=True)
    price = Column(Integer, nullable=True, default=0)
    image_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(String(80), nullable=False, default="aadhaar")
    document_url = Column(String(500), nullable=False)
    document_reference = Column(String(200), nullable=True)
    masked_reference = Column(String(200), nullable=True)
    status = Column(String(30), default="pending")
    review_notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class FavoriteBarber(Base):
    __tablename__ = "favorite_barbers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("customer_id", "shop_id", name="uq_favorite_customer_shop"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    barber_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review = Column(Text, nullable=True)
    service_feedback = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HairstyleCategory(Base):
    __tablename__ = "hairstyle_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    price_range = Column(String(80), nullable=True)
    active = Column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "booking_date",
            "slot_time",
            name="uq_shop_booking_slot",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    shop_id = Column(
        Integer,
        ForeignKey("shops.id"),
        nullable=False,
        index=True,
    )

    customer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    service_id = Column(
        Integer,
        ForeignKey("services.id"),
        nullable=False,
    )

    booking_date = Column(String(10), nullable=False, index=True)
    slot_time = Column(String(10), nullable=False)

    status = Column(
        String(30),
        default="booked",
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id = Column(Integer, primary_key=True, index=True)

    shop_id = Column(
        Integer,
        ForeignKey("shops.id"),
        nullable=False,
        index=True,
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=True,
    )

    customer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    position = Column(Integer, nullable=False)

    status = Column(
        String(30),
        default="waiting",
        nullable=False,
    )

    joined_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)

    is_read = Column(
        Boolean,
        default=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )