import uuid
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from novaapi.models.base import Base, IdMixin, TimestampMixin


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('active','blocked')", name="status_valid"),)

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str | None] = mapped_column(String(128))
    photo_url: Mapped[str | None] = mapped_column(String(512))
    language: Mapped[str] = mapped_column(String(5), default="en", server_default="en", nullable=False)  # ru | en (bot + Mini App)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    admin_note: Mapped[str | None] = mapped_column(Text)
    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)


class Wallet(Base, IdMixin, TimestampMixin):
    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint("status IN ('active','frozen')", name="status_valid"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    # Internal human-readable wallet ID (NOT a blockchain address).
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", nullable=False)
    user: Mapped[User] = relationship(back_populates="wallet")
