from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import engine, Base, ensure_schema

from app.routes import (
    auth,
    customer,
    barber,
    bookings,
    queue,
    services,
)


# =========================================================
# DATABASE
# =========================================================

ensure_schema()
Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="TrimQ",
    version="1.0.0",
    description="Smart Barber Booking and Queue Management System"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "https://trimq-frontend.vercel.app",

        # Local development
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROUTES
# =========================================================

app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(barber.router)
app.include_router(bookings.router)
app.include_router(queue.router)
app.include_router(services.router)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "TrimQ API is running",
        "status": "online",
        "version": "1.0.0"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }