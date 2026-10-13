from uuid import uuid4
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth0 import require_admin_auth
from db.engine import get_db
from models.customer import Customer
from models.shipment import Shipment, ShipmentStatus
from models.package import Package

router = APIRouter(prefix="/admin", tags=["admin"])

# ─── Pydantic schemas ────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    address: str

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None

class CustomerResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone_number: str
    address: str
    model_config = {"from_attributes": True}

class ShipmentCreate(BaseModel):
    customer_id: str
    tracking_number: str
    status: ShipmentStatus
    carrier: str
    origin: str
    destination: str
    estimated_delivery: date
    last_update: Optional[datetime] = None

class ShipmentUpdate(BaseModel):
    status: Optional[ShipmentStatus] = None
    carrier: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    estimated_delivery: Optional[date] = None
    last_update: Optional[datetime] = None

class ShipmentResponse(BaseModel):
    id: str
    customer_id: str
    tracking_number: str
    status: ShipmentStatus
    carrier: str
    origin: str
    destination: str
    estimated_delivery: date
    last_update: datetime
    model_config = {"from_attributes": True}

class PackageCreate(BaseModel):
    shipment_id: str
    description: str
    weight_kg: Decimal
    declared_value: Decimal

class PackageUpdate(BaseModel):
    description: Optional[str] = None
    weight_kg: Optional[Decimal] = None
    declared_value: Optional[Decimal] = None

class PackageResponse(BaseModel):
    id: str
    shipment_id: str
    description: str
    weight_kg: Decimal
    declared_value: Decimal
    model_config = {"from_attributes": True}

# ─── Customers ───────────────────────────────────────────────────────────────

@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Customer).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    customer = Customer(id=str(uuid4()), **body.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer

@router.delete("/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.delete(customer)
    await db.commit()

# ─── Shipments ───────────────────────────────────────────────────────────────

@router.get("/shipments", response_model=list[ShipmentResponse])
async def list_shipments(
    customer_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    q = select(Shipment)
    if customer_id:
        q = q.where(Shipment.customer_id == customer_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/shipments", response_model=ShipmentResponse, status_code=201)
async def create_shipment(
    body: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    data = body.model_dump()
    data["id"] = str(uuid4())
    data["last_update"] = data.get("last_update") or datetime.utcnow()
    shipment = Shipment(**data)
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)
    return shipment

@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment

@router.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: str,
    body: ShipmentUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    updates = body.model_dump(exclude_none=True)
    if updates:
        updates["last_update"] = datetime.utcnow()
    for field, value in updates.items():
        setattr(shipment, field, value)
    await db.commit()
    await db.refresh(shipment)
    return shipment

@router.delete("/shipments/{shipment_id}", status_code=204)
async def delete_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    await db.delete(shipment)
    await db.commit()

# ─── Packages ────────────────────────────────────────────────────────────────

@router.get("/packages", response_model=list[PackageResponse])
async def list_packages(
    shipment_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    q = select(Package)
    if shipment_id:
        q = q.where(Package.shipment_id == shipment_id)
    result = await db.execute(q)
    return result.scalars().all()

@router.post("/packages", response_model=PackageResponse, status_code=201)
async def create_package(
    body: PackageCreate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    package = Package(id=str(uuid4()), **body.model_dump())
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return package

@router.put("/packages/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: str,
    body: PackageUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(package, field, value)
    await db.commit()
    await db.refresh(package)
    return package

@router.delete("/packages/{package_id}", status_code=204)
async def delete_package(
    package_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    await db.delete(package)
    await db.commit()
