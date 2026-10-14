import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.session import Session, SessionState
from models.shipment import Shipment
from models.package import Package

logger = logging.getLogger(__name__)


async def lookup_shipments(session: Session, db: AsyncSession) -> dict:
    """
    Look up all shipments for the verified customer.

    SECURITY INVARIANT: This function ALWAYS uses session.verified_customer_id.
    It accepts NO customer_id argument. Even if the model somehow provided one,
    it would be ignored — the function signature does not accept it.
    """
    # Double-check state — the tool registry should have already blocked this call
    # if state != VERIFIED, but we enforce it here too as defense-in-depth.
    if session.state != SessionState.VERIFIED:
        logger.warning(
            "lookup_shipments called in non-VERIFIED state: %s (session=%s)",
            session.state,
            session.session_id,
        )
        return {"error": "You must be verified to access shipment information."}

    if not session.verified_customer_id:
        logger.error("VERIFIED state but no verified_customer_id (session=%s)", session.session_id)
        return {"error": "Session error. Please contact support."}

    # SECURITY: All queries are scoped to session.verified_customer_id
    result = await db.execute(
        select(Shipment).where(Shipment.customer_id == session.verified_customer_id)
    )
    shipments = result.scalars().all()

    if not shipments:
        return {"shipments": [], "message": "No shipments found for your account."}

    return {
        "shipments": [
            {
                "id": s.id,
                "tracking_number": s.tracking_number,
                "status": s.status.value,
                "carrier": s.carrier,
                "origin": s.origin,
                "destination": s.destination,
                "estimated_delivery": str(s.estimated_delivery),
                "last_update": s.last_update.isoformat() if s.last_update else None,
            }
            for s in shipments
        ]
    }


async def lookup_shipment_detail(
    session: Session,
    tracking_number: str,
    db: AsyncSession,
) -> dict:
    """
    Look up a specific shipment by tracking number.

    SECURITY: Scoped to session.verified_customer_id — a shipment belonging to a
    different customer will return "not found", not the actual data.
    """
    if session.state != SessionState.VERIFIED or not session.verified_customer_id:
        return {"error": "You must be verified to access shipment information."}

    result = await db.execute(
        select(Shipment).where(
            Shipment.tracking_number == tracking_number,
            Shipment.customer_id == session.verified_customer_id,  # SECURITY: scoped
        )
    )
    shipment = result.scalar_one_or_none()

    if not shipment:
        # Do not reveal whether the tracking number exists for another customer
        return {"error": f"No shipment found with tracking number {tracking_number} on your account."}

    # Fetch packages
    pkg_result = await db.execute(
        select(Package).where(Package.shipment_id == shipment.id)
    )
    packages = pkg_result.scalars().all()

    return {
        "shipment": {
            "id": shipment.id,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status.value,
            "carrier": shipment.carrier,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "estimated_delivery": str(shipment.estimated_delivery),
            "last_update": shipment.last_update.isoformat() if shipment.last_update else None,
            "packages": [
                {
                    "description": p.description,
                    "weight_kg": float(p.weight_kg),
                    "declared_value": float(p.declared_value),
                }
                for p in packages
            ],
        }
    }
