import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.session import Session, transition_to_code_sent
from domain.verification import generate_code
from domain.identity import fields_match_customer
from models.customer import Customer

logger = logging.getLogger(__name__)


async def verify_identity(
    session: Session,
    first_name: str,
    last_name: str,
    address: str,
    phone: str,
    db: AsyncSession,
) -> dict:
    """
    Try to match the provided fields against a customer record.
    On match: generate a verification code, transition session to CODE_SENT.
    On no match: return a neutral failure message (do not reveal whether the customer exists).

    SECURITY: This function never returns customer_id to the model.
    The customer_id is stored in session.pending_customer_id only.
    """
    # Fetch all customers — for 25 customers this is fine; add pagination if data grows
    result = await db.execute(select(Customer))
    customers = result.scalars().all()

    matched_customer = None
    for customer in customers:
        if fields_match_customer(
            first_name, last_name, address, phone,
            customer.first_name, customer.last_name,
            customer.address, customer.phone_number,
        ):
            matched_customer = customer
            break

    if matched_customer is None:
        logger.info("Identity verification: no match found (session=%s)", session.session_id)
        # Store what was provided so the model can ask for corrections
        session.collected_fields.update({
            k: v for k, v in {
                "first_name": first_name,
                "last_name": last_name,
                "address": address,
                "phone": phone,
            }.items() if v
        })
        return {
            "success": False,
            "message": (
                "I wasn't able to verify your identity with those details. "
                "Please double-check your name, address, and phone number and try again."
            ),
        }

    # Match found — generate code, transition session
    plain_code, code_hash = generate_code()

    # SECURITY: pending_customer_id is set here. The model never sees this value.
    transition_to_code_sent(
        session,
        pending_customer_id=str(matched_customer.id),
        code_hash=code_hash,
        first_name=matched_customer.first_name,
    )

    # Mock SMS: log the code to console (never log to a persistent file in production)
    logger.info(
        "MOCK SMS: Sending verification code to phone ending in ...%s [session=%s]",
        phone[-4:] if len(phone) >= 4 else "****",
        session.session_id,
    )
    # Print clearly for development visibility
    print(f"\n{'='*40}")
    print(f"MOCK SMS VERIFICATION CODE: {plain_code}")
    print(f"Session: {session.session_id}")
    print(f"{'='*40}\n")

    return {
        "success": True,
        "message": (
            f"I've sent a 6-digit verification code to your phone. "
            f"Please enter it in the box that just appeared."
        ),
        "show_modal": True,
    }
