import uuid
import enum
from sqlalchemy import String, Date, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from db.engine import Base


class ShipmentStatus(str, enum.Enum):
    label_created = "label_created"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    exception = "exception"


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(
        String, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tracking_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[ShipmentStatus] = mapped_column(SAEnum(ShipmentStatus), nullable=False)
    carrier: Mapped[str] = mapped_column(String, nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    estimated_delivery: Mapped[Date] = mapped_column(Date, nullable=False)
    last_update: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
