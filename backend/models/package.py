import uuid
from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.engine import Base


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_id: Mapped[str] = mapped_column(
        String, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    declared_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
