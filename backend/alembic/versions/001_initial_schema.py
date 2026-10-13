"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_phone_number"), "customers", ["phone_number"], unique=False)

    # shipments table
    shipment_status_enum = sa.Enum(
        "label_created",
        "in_transit",
        "out_for_delivery",
        "delivered",
        "exception",
        name="shipmentstatus",
    )
    op.create_table(
        "shipments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("tracking_number", sa.String(), nullable=False),
        sa.Column("status", shipment_status_enum, nullable=False),
        sa.Column("carrier", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("estimated_delivery", sa.Date(), nullable=False),
        sa.Column(
            "last_update",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_number"),
    )
    op.create_index(op.f("ix_shipments_customer_id"), "shipments", ["customer_id"], unique=False)

    # packages table
    op.create_table(
        "packages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("declared_value", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_packages_shipment_id"), "packages", ["shipment_id"], unique=False)

    # chat_sessions table
    session_state_enum = sa.Enum(
        "anonymous",
        "collecting_identity",
        "code_sent",
        "awaiting_code",
        "verified",
        "escalated_to_human",
        name="sessionstate",
    )
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("state", session_state_enum, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transcript", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_sessions_customer_id"), "chat_sessions", ["customer_id"], unique=False
    )
    op.create_index(op.f("ix_chat_sessions_state"), "chat_sessions", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_sessions_state"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_customer_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
    sa.Enum(name="sessionstate").drop(op.get_bind())

    op.drop_index(op.f("ix_packages_shipment_id"), table_name="packages")
    op.drop_table("packages")

    op.drop_index(op.f("ix_shipments_customer_id"), table_name="shipments")
    op.drop_table("shipments")
    sa.Enum(name="shipmentstatus").drop(op.get_bind())

    op.drop_index(op.f("ix_customers_phone_number"), table_name="customers")
    op.drop_table("customers")
