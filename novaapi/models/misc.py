import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from novaapi.models.base import Base, IdMixin, TimestampMixin


class Notification(Base, IdMixin, TimestampMixin):
    """Outbox: bot worker sends 'pending' rows. dedupe_key prevents double sending."""
    __tablename__ = "notifications"
    __table_args__ = (CheckConstraint("status IN ('pending','sent','failed','skipped')", name="status_valid"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base, IdMixin, TimestampMixin):
    __tablename__ = "notification_preferences"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    transfers: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    announcements: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    # Critical notifications (restriction, maintenance) are always delivered.


class Setting(Base, IdMixin, TimestampMixin):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)


class SupportTicket(Base, IdMixin, TimestampMixin):
    __tablename__ = "support_tickets"
    __table_args__ = (CheckConstraint("status IN ('open','in_progress','closed')", name="status_valid"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open", nullable=False, index=True)


class Watchlist(Base, IdMixin, TimestampMixin):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="user_asset"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
