import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from novaapi.models.base import Base, IdMixin, TimestampMixin


class AdminRole(Base, IdMixin, TimestampMixin):
    __tablename__ = "admin_roles"
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # OWNER, SUPER_ADMIN, ADMIN, MODERATOR, SUPPORT
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # lower = more powerful; no self-escalation


class AdminPermission(Base, IdMixin, TimestampMixin):
    __tablename__ = "admin_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission", name="role_permission"),)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)


class Admin(Base, IdMixin, TimestampMixin):
    __tablename__ = "admins"
    __table_args__ = (CheckConstraint("status IN ('active','disabled')", name="status_valid"),)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(128))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminLog(Base, IdMixin, TimestampMixin):
    """Append-only audit log (UPDATE/DELETE blocked by DB trigger)."""
    __tablename__ = "admin_logs"
    admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64), index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class AdminSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "admin_sessions"
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
