import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from db.engine import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
