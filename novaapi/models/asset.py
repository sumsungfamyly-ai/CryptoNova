import uuid
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from novaapi.models.base import AMOUNT, Base, IdMixin, TimestampMixin


class Asset(Base, IdMixin, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("virtual_price >= 0", name="price_nonneg"),
        CheckConstraint("total_supply >= 0", name="supply_nonneg"),
        CheckConstraint("max_supply IS NULL OR total_supply <= max_supply", name="supply_within_max"),
        CheckConstraint("decimal_precision BETWEEN 0 AND 18", name="precision_range"),
    )
    symbol: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    icon: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(24), default="popular", server_default="popular")
    virtual_price: Mapped[Decimal] = mapped_column(AMOUNT, default=0, server_default="0", nullable=False)
    total_supply: Mapped[Decimal] = mapped_column(AMOUNT, default=0, server_default="0", nullable=False)
    max_supply: Mapped[Decimal | None] = mapped_column(AMOUNT)  # NULL = unlimited
    decimal_precision: Mapped[int] = mapped_column(Integer, default=8, server_default="8", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Balance(Base, IdMixin, TimestampMixin):
    """Projection of the ledger. Mutated ONLY by LedgerService."""
    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint("wallet_id", "asset_id", name="wallet_asset"),
        # Only the system treasury may go negative (it is the counter-party of issuance).
        CheckConstraint("amount >= 0 OR allow_negative", name="no_negative"),
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, default=0, server_default="0", nullable=False)
    allow_negative: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)


class TokenIssuance(Base, IdMixin, TimestampMixin):
    __tablename__ = "token_issuance"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"))
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class AssetPrice(Base, IdMixin, TimestampMixin):
    """Recorded virtual price points (real simulator data used by charts)."""
    __tablename__ = "asset_prices"
    __table_args__ = (CheckConstraint("price >= 0", name="price_nonneg"),)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
