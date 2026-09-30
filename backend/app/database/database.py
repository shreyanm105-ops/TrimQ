import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./trimq.db"
)


if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )

elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )


if DATABASE_URL.startswith("sqlite"):

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False
        }
    )

else:

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def ensure_schema():
    """Add missing database columns without deleting existing data."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    def add_column_if_missing(table_name: str, column_name: str, column_type: str):
        if table_name not in existing_tables:
            return

        columns = [column["name"] for column in inspector.get_columns(table_name)]
        if column_name in columns:
            return

        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
            )

    add_column_if_missing("shops", "official_name", "VARCHAR(200)")
    add_column_if_missing("shops", "tagline", "VARCHAR(220)")
    add_column_if_missing("shops", "city", "VARCHAR(120)")
    add_column_if_missing("shops", "state", "VARCHAR(120)")
    add_column_if_missing("shops", "pincode", "VARCHAR(20)")
    add_column_if_missing("shops", "latitude", "FLOAT")
    add_column_if_missing("shops", "longitude", "FLOAT")
    add_column_if_missing("shops", "shop_logo", "VARCHAR(500)")
    add_column_if_missing("shops", "shop_cover", "VARCHAR(500)")
    add_column_if_missing("shops", "weekly_holidays", "VARCHAR(200)")
    add_column_if_missing("shops", "about_shop", "TEXT")
    add_column_if_missing("shops", "amenities", "TEXT")
    add_column_if_missing("shops", "verification_status", "VARCHAR(30)")
    add_column_if_missing("shops", "profile_status", "VARCHAR(30)")
    add_column_if_missing("shops", "is_verified", "BOOLEAN")
    add_column_if_missing("shops", "average_rating", "FLOAT")
    add_column_if_missing("shops", "rating_count", "INTEGER")
    add_column_if_missing("shops", "experience_years", "INTEGER")
    add_column_if_missing("shops", "service_start_price", "INTEGER")
    add_column_if_missing("shops", "shop_slug", "VARCHAR(120)")

    add_column_if_missing("services", "category", "VARCHAR(60)")

    add_column_if_missing("users", "gender", "VARCHAR(20)")
    add_column_if_missing("users", "profile_photo", "VARCHAR(500)")


ensure_schema()


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()