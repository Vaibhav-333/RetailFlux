"""
RetailFlux — Demo Data Seeder
Populates PostgreSQL + MongoDB with realistic fashion/clothing data.

Usage (inside docker-compose):
    docker-compose exec api python scripts/seed_demo.py

Usage (local, after `make up`):
    python scripts/seed_demo.py
"""
import asyncio
import io
import os
import random
import sys
import uuid
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo_root, "apps", "api"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.company import Company
from app.models.user import User, UserRole

# ── Constants ─────────────────────────────────────────────────────────────────

COMPANY_ID = "00000000-0000-0000-0000-000000000001"
COMPANY_UUID = uuid.UUID(COMPANY_ID)

SKUS = [
    "BLZ-BLK-M", "BLZ-BLK-L", "BLZ-NVY-M", "SHT-WHT-L", "SHT-WHT-M",
    "JNS-BLU-32", "JNS-BLU-34", "JNS-GRY-32", "DRS-RED-S", "DRS-RED-M",
    "JKT-GRY-XL", "JKT-BLK-L", "SKT-BEI-S", "SKT-BEI-M", "TRS-KHK-32",
    "TRS-BLK-34", "TOP-WHT-XS", "TOP-BLK-S", "HOD-GRN-M", "HOD-BLU-L",
]
REGIONS = ["North", "South", "East", "West", "Central"]
CHANNELS = ["online", "retail", "wholesale"]
CAMPAIGNS = [f"CAMP-{i:03d}" for i in range(1, 8)]
WAREHOUSES = ["WH-North", "WH-South", "WH-East"]
SUPPLIERS = [f"SUP-{i:02d}" for i in range(1, 7)]
CATEGORIES = ["Outerwear", "Footwear", "Accessories", "Tops", "Bottoms"]


# ── Postgres seed ─────────────────────────────────────────────────────────────

async def seed_postgres() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM app.companies"))
        if result.scalar() > 0:
            print("✓ Postgres demo data already exists — skipping")
            await engine.dispose()
            return

        company = Company(id=COMPANY_UUID, name="Verve Fashion Co.", plan="pro")
        session.add(company)
        await session.flush()

        demo_users = [
            ("Demo CEO",           "ceo@retailflux.demo",         UserRole.CEO),
            ("Sales Manager",      "sales@retailflux.demo",       UserRole.SALES),
            ("Marketing Lead",     "marketing@retailflux.demo",   UserRole.MARKETING),
            ("Finance Controller", "finance@retailflux.demo",     UserRole.FINANCE),
            ("Ops Manager",        "ops@retailflux.demo",         UserRole.OPERATIONS),
            ("Procurement Head",   "procurement@retailflux.demo", UserRole.PROCUREMENT),
        ]
        for name, email, role in demo_users:
            session.add(User(
                name=name,
                email=email,
                password_hash=hash_password("demo1234"),
                role=role,
                company_id=COMPANY_UUID,
            ))

        await session.commit()

    print("✓ Postgres seeded — Verve Fashion Co. + 6 users (password: demo1234)")
    for _, email, role in demo_users:
        print(f"  {role.value:15s}  {email}")
    await engine.dispose()


# ── MongoDB seed ──────────────────────────────────────────────────────────────

def seed_mongodb() -> None:
    import pymongo

    client = pymongo.MongoClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DATABASE]

    today = date.today()
    days = [today - timedelta(days=i) for i in range(90, 0, -1)]

    # ── staging_sales ────────────────────────────────────────────────────────
    col = db["staging_sales"]
    if col.count_documents({"_company_id": COMPANY_ID}) == 0:
        records = []
        for d in days:
            for sku in random.sample(SKUS, k=random.randint(5, 12)):
                qty = random.randint(1, 40)
                price = round(random.uniform(30, 250), 2)
                records.append({
                    "_company_id": COMPANY_ID,
                    "sku": sku,
                    "date": d.isoformat(),
                    "quantity": qty,
                    "revenue": round(qty * price, 2),
                    "region": random.choice(REGIONS),
                    "channel": random.choice(CHANNELS),
                    "category": random.choice(CATEGORIES),
                })
        col.insert_many(records)
        print(f"✓ staging_sales   — {len(records):,} records")
    else:
        print("✓ staging_sales   — already seeded")

    # ── staging_marketing ────────────────────────────────────────────────────
    col = db["staging_marketing"]
    if col.count_documents({"_company_id": COMPANY_ID}) == 0:
        records = []
        for d in days:
            for camp in CAMPAIGNS:
                impressions = random.randint(1000, 20000)
                ctr = random.uniform(0.01, 0.05)
                clicks = int(impressions * ctr)
                conv_rate = random.uniform(0.02, 0.08)
                records.append({
                    "_company_id": COMPANY_ID,
                    "campaign_id": camp,
                    "date": d.isoformat(),
                    "spend": round(random.uniform(50, 500), 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": int(clicks * conv_rate),
                })
        col.insert_many(records)
        print(f"✓ staging_marketing — {len(records):,} records")
    else:
        print("✓ staging_marketing — already seeded")

    # ── staging_operations ───────────────────────────────────────────────────
    col = db["staging_operations"]
    if col.count_documents({"_company_id": COMPANY_ID}) == 0:
        records = []
        for d in days:
            for sku in SKUS:
                for wh in WAREHOUSES:
                    records.append({
                        "_company_id": COMPANY_ID,
                        "sku": sku,
                        "warehouse": wh,
                        "date": d.isoformat(),
                        "stock_level": random.randint(0, 200),
                        "reorder_point": 20,
                    })
        col.insert_many(records)
        print(f"✓ staging_operations — {len(records):,} records")
    else:
        print("✓ staging_operations — already seeded")

    # ── staging_finance ──────────────────────────────────────────────────────
    col = db["staging_finance"]
    if col.count_documents({"_company_id": COMPANY_ID}) == 0:
        records = []
        for d in days:
            for cat in CATEGORIES:
                revenue = round(random.uniform(500, 5000), 2)
                cogs = round(revenue * random.uniform(0.45, 0.65), 2)
                records.append({
                    "_company_id": COMPANY_ID,
                    "date": d.isoformat(),
                    "category": cat,
                    "revenue": revenue,
                    "cogs": cogs,
                    "gross_profit": round(revenue - cogs, 2),
                })
        col.insert_many(records)
        print(f"✓ staging_finance  — {len(records):,} records")
    else:
        print("✓ staging_finance  — already seeded")

    # ── staging_procurement ──────────────────────────────────────────────────
    col = db["staging_procurement"]
    if col.count_documents({"_company_id": COMPANY_ID}) == 0:
        records = []
        for d in days:
            for _ in range(random.randint(3, 8)):
                qty = random.randint(10, 200)
                records.append({
                    "_company_id": COMPANY_ID,
                    "sku": random.choice(SKUS),
                    "supplier_id": random.choice(SUPPLIERS),
                    "date": d.isoformat(),
                    "quantity": qty,
                    "unit_cost": round(random.uniform(10, 80), 2),
                    "lead_days": random.randint(3, 21),
                })
        col.insert_many(records)
        print(f"✓ staging_procurement — {len(records):,} records")
    else:
        print("✓ staging_procurement — already seeded")

    client.close()


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n── RetailFlux Demo Seeder ────────────────────────────────")
    await seed_postgres()
    print()
    seed_mongodb()
    print("\n✓ Done. Log in at http://localhost:3000\n")


if __name__ == "__main__":
    asyncio.run(main())
