#!/usr/bin/env python3
"""
Seed script for SecureShip database.
Generates reproducible test data: 25 customers, 40-60 shipments, 1-3 packages each.
"""
import os
import random
import uuid
from datetime import date, timedelta

import psycopg2
from faker import Faker

random.seed(42)
fake = Faker("en_US")
Faker.seed(42)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://secureship:secureship@localhost:5432/secureship",
)

# Convert asyncpg URL to psycopg2 DSN
dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

CARRIERS = ["FedEx", "UPS", "USPS", "DHL", "Amazon Logistics"]
CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL",
    "Fort Worth, TX", "Columbus, OH", "Charlotte, NC", "Indianapolis, IN",
    "San Francisco, CA", "Seattle, WA", "Denver, CO", "Nashville, TN",
]

SHIPMENT_STATUS_WEIGHTS = [
    ("in_transit", 0.50),
    ("delivered", 0.30),
    ("out_for_delivery", 0.10),
    ("exception", 0.10),
]

PACKAGE_DESCRIPTIONS = [
    "Electronics - Laptop", "Clothing and Accessories", "Books and Media",
    "Kitchen Appliances", "Sporting Goods", "Toys and Games", "Health Products",
    "Office Supplies", "Automotive Parts", "Home Decor", "Musical Instruments",
    "Camera Equipment", "Power Tools", "Garden Supplies", "Pet Supplies",
]


def weighted_choice(choices):
    items, weights = zip(*choices)
    return random.choices(items, weights=weights, k=1)[0]


def generate_tracking_number(carrier: str) -> str:
    prefix = {
        "FedEx": "7489",
        "UPS": "1Z",
        "USPS": "9400",
        "DHL": "1234567890",
        "Amazon Logistics": "TBA",
    }.get(carrier, "")
    suffix = "".join([str(random.randint(0, 9)) for _ in range(14)])
    return f"{prefix}{suffix}"


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    print("Creating customers...")
    customer_ids = []
    for _ in range(25):
        cid = str(uuid.uuid4())
        first_name = fake.first_name()
        last_name = fake.last_name()
        # E.164 US phone number
        area_code = random.randint(200, 999)
        number = random.randint(1000000, 9999999)
        phone = f"+1{area_code}{number}"
        address = fake.address().replace("\n", ", ")

        cur.execute(
            """
            INSERT INTO customers (id, first_name, last_name, phone_number, address)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (cid, first_name, last_name, phone, address),
        )
        customer_ids.append(cid)

    conn.commit()

    print("Creating shipments and packages...")
    num_shipments = random.randint(40, 60)
    tracking_numbers = set()

    for _ in range(num_shipments):
        shipment_id = str(uuid.uuid4())
        customer_id = random.choice(customer_ids)
        carrier = random.choice(CARRIERS)

        # Ensure unique tracking numbers
        while True:
            tracking = generate_tracking_number(carrier)
            if tracking not in tracking_numbers:
                tracking_numbers.add(tracking)
                break

        status = weighted_choice(SHIPMENT_STATUS_WEIGHTS)
        origin = random.choice(CITIES)
        destination = random.choice([c for c in CITIES if c != origin])
        days_offset = random.randint(1, 14)
        estimated_delivery = date.today() + timedelta(days=days_offset)
        last_update = fake.date_time_this_year()

        cur.execute(
            """
            INSERT INTO shipments
                (id, customer_id, tracking_number, status, carrier, origin, destination,
                 estimated_delivery, last_update)
            VALUES (%s, %s, %s, %s::shipmentstatus, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                shipment_id, customer_id, tracking, status,
                carrier, origin, destination, estimated_delivery, last_update,
            ),
        )

        # 1-3 packages per shipment
        num_packages = random.randint(1, 3)
        for _ in range(num_packages):
            pkg_id = str(uuid.uuid4())
            description = random.choice(PACKAGE_DESCRIPTIONS)
            weight_kg = round(random.uniform(0.1, 30.0), 3)
            declared_value = round(random.uniform(10.0, 2000.0), 2)

            cur.execute(
                """
                INSERT INTO packages (id, shipment_id, description, weight_kg, declared_value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (pkg_id, shipment_id, description, weight_kg, declared_value),
            )

    conn.commit()
    cur.close()
    conn.close()

    print(f"Done. Created 25 customers, {num_shipments} shipments with packages.")


if __name__ == "__main__":
    main()
