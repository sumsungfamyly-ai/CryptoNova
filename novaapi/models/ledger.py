import uuid
from decimal import Decimal
from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from novaapi.models.base import AMOUNT, Base, IdMixin, TimestampMixin

TX_TYPES = "('transfer','admin_credit','admin_debit','issuance','initial_grant','fee','swap_in','swap_out')"
TX_STATUSES = "('completed','pending','cancelled','failed')"


class Transaction(Base, IdMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(f"type IN {TX_TYPES}", name="type_valid"),
        CheckConstraint(f"status IN {TX_STATUSES}", name="status_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("fee >= 0", name="fee_nonneg"),
    )
    type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="completed", nullable=False, index=True)
    # Unique per initiator scope; protects against duplicate submission.
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    fee: Mapped[Decimal] = mapped_column(AMOUNT, default=0, server_default="0", nullable=False)
    from_wallet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), index=True)
    to_wallet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), index=True)
    initiated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id", ondelete="RESTRICT"))
    reason: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(String(256))


class LedgerEntry(Base, IdMixin, TimestampMixin):
    """Append-only. Entries of one transaction+asset must sum to 0 (DB trigger)."""
    __tablename__ = "ledger_entries"
    __table_args__ = (CheckConstraint("amount <> 0", name="amount_nonzero"),)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, index=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)  # signed
    balance_after: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
