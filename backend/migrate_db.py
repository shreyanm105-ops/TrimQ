from sqlalchemy import inspect, text

from app.database.database import engine, Base
from app.database import models


def add_column_if_missing(
    connection,
    table_name,
    column_name,
    column_definition
):
    inspector = inspect(connection)

    if table_name not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    if column_name not in columns:
        print(f"Adding column: {table_name}.{column_name}")

        connection.execute(
            text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} "
                f"{column_definition}"
            )
        )


def migrate():

    print("Starting TrimQ database migration...")

    with engine.begin() as connection:

        # USERS
        add_column_if_missing(
            connection, "users", "password_hash", "VARCHAR(255)"
        )

        add_column_if_missing(
            connection, "users", "phone", "VARCHAR(30)"
        )

        add_column_if_missing(
            connection, "users", "role", "VARCHAR(20)"
        )

        add_column_if_missing(
            connection, "users", "is_active", "BOOLEAN"
        )

        # SHOPS
        add_column_if_missing(
            connection, "shops", "owner_id", "INTEGER"
        )

        add_column_if_missing(
            connection, "shops", "description", "TEXT"
        )

        add_column_if_missing(
            connection, "shops", "opening_time", "VARCHAR(10)"
        )

        add_column_if_missing(
            connection, "shops", "closing_time", "VARCHAR(10)"
        )

        # SERVICES
        add_column_if_missing(
            connection, "services", "shop_id", "INTEGER"
        )

        add_column_if_missing(
            connection, "services", "description", "TEXT"
        )

        add_column_if_missing(
            connection, "services", "price", "INTEGER"
        )

        add_column_if_missing(
            connection, "services", "duration_minutes", "INTEGER"
        )

        add_column_if_missing(
            connection, "services", "is_active", "BOOLEAN"
        )

        # BOOKINGS
        add_column_if_missing(
            connection, "bookings", "shop_id", "INTEGER"
        )

        add_column_if_missing(
            connection, "bookings", "customer_id", "INTEGER"
        )

        add_column_if_missing(
            connection, "bookings", "service_id", "INTEGER"
        )

        add_column_if_missing(
            connection, "bookings", "booking_date", "VARCHAR(10)"
        )

        add_column_if_missing(
            connection, "bookings", "slot_time", "VARCHAR(10)"
        )

        add_column_if_missing(
            connection, "bookings", "status", "VARCHAR(30)"
        )

        # NEW TABLES
        Base.metadata.create_all(bind=connection)

    print()
    print("====================================")
    print("TrimQ database migration completed!")
    print("====================================")


if __name__ == "__main__":
    migrate()