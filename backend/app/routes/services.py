from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..database.database import get_db
from ..database.models import Service, Shop, User
from ..schemas.service import ServiceCreate

router = APIRouter(
    prefix="/api/services",
    tags=["Services"]
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
# GET ALL ACTIVE SERVICES
# =========================================================

@router.get("/")
def get_services(
    shop_id: int | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Service).filter(
        Service.is_active == True
    )

    if shop_id:
        query = query.filter(
            Service.shop_id == shop_id
        )

    services = query.order_by(
        Service.id.asc()
    ).all()

    return services


# =========================================================
# GET SINGLE SERVICE
# =========================================================

@router.get("/{service_id}")
def get_service(
    service_id: int,
    db: Session = Depends(get_db)
):

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.is_active == True
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    return service


# =========================================================
# BARBER CREATE SERVICE
# =========================================================

@router.post("/")
def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can create services"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Create your shop first"
        )

    existing_service = db.query(Service).filter(
        Service.shop_id == shop.id,
        Service.name == service_data.name,
        Service.is_active == True
    ).first()

    if existing_service:
        raise HTTPException(
            status_code=400,
            detail="This service already exists"
        )

    if service_data.price < 0:
        raise HTTPException(
            status_code=400,
            detail="Price cannot be negative"
        )

    if service_data.duration_minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Duration must be greater than 0"
        )

    service = Service(
        shop_id=shop.id,
        name=service_data.name.strip(),
        description=service_data.description,
        price=service_data.price,
        duration_minutes=service_data.duration_minutes,
        is_active=True
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service


# =========================================================
# BARBER UPDATE SERVICE
# =========================================================

@router.put("/{service_id}")
def update_service(
    service_id: int,
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can update services"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.shop_id == shop.id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    if service_data.price < 0:
        raise HTTPException(
            status_code=400,
            detail="Price cannot be negative"
        )

    if service_data.duration_minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Duration must be greater than 0"
        )

    service.name = service_data.name.strip()
    service.description = service_data.description
    service.price = service_data.price
    service.duration_minutes = service_data.duration_minutes
    service.is_active = service_data.is_active

    db.commit()
    db.refresh(service)

    return service


# =========================================================
# BARBER DEACTIVATE SERVICE
# =========================================================

@router.delete("/{service_id}")
def deactivate_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can remove services"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.shop_id == shop.id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    # Actual database row delete nahi karenge.
    # Service inactive karenge so old bookings remain safe.
    service.is_active = False

    db.commit()

    return {
        "message": "Service deactivated successfully",
        "service_id": service.id
    }


# =========================================================
# BARBER REACTIVATE SERVICE
# =========================================================

@router.patch("/{service_id}/activate")
def activate_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "barber":
        raise HTTPException(
            status_code=403,
            detail="Only barber can activate services"
        )

    shop = db.query(Shop).filter(
        Shop.owner_id == current_user.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=404,
            detail="Shop not found"
        )

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.shop_id == shop.id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    service.is_active = True

    db.commit()
    db.refresh(service)

    return {
        "message": "Service activated successfully",
        "service": service
    }


# =========================================================
# BARBER VIEW ALL OWN SERVICES
# =========================================================

@router.get("/barber/my")
def get_my_services(
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

    services = db.query(Service).filter(
        Service.shop_id == shop.id
    ).order_by(
        Service.id.asc()
    ).all()

    return {
        "shop_id": shop.id,
        "shop_name": shop.name,
        "services": services
    }