import hashlib, hmac, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.api.deps import get_session
from novaapi.core.config import settings
from novaapi.models import Admin, AdminLog, AdminPermission, AdminRole, AdminSession
from novaapi.security.tokens import decode_token

COOKIE = "nova_admin"


def csrf_for(session_id: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"csrf:{session_id}".encode(), hashlib.sha256).hexdigest()


@dataclass
class Ctx:
    admin: Admin
    role: AdminRole
    perms: set
    session_id: str
    ip: str


def client_ip(r: Request) -> str:
    return (r.headers.get("x-forwarded-for", "").split(",")[0].strip() or (r.client.host if r.client else ""))


async def current_admin(request: Request, s: AsyncSession = Depends(get_session)) -> Ctx:
    sid = decode_token(request.cookies.get(COOKIE, ""), settings.secret_key)
    if not sid:
        raise HTTPException(401, "not authenticated")
    sess = (await s.execute(select(AdminSession).where(AdminSession.id == uuid.UUID(sid)))).scalar_one_or_none()
    if not sess or sess.revoked or sess.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "session expired")
    admin = (await s.execute(select(Admin).where(Admin.id == sess.admin_id))).scalar_one()
    if admin.status != "active":
        raise HTTPException(401, "account disabled")
    if request.method not in ("GET", "HEAD", "OPTIONS") and not hmac.compare_digest(request.headers.get("x-csrf-token", ""), csrf_for(sid)):
        raise HTTPException(403, "bad CSRF token")
    role = (await s.execute(select(AdminRole).where(AdminRole.id == admin.role_id))).scalar_one()
    perms = {p for p in (await s.execute(select(AdminPermission.permission).where(AdminPermission.role_id == role.id))).scalars()}
    return Ctx(admin, role, perms, sid, client_ip(request))


def require(perm: str):
    async def dep(ctx: Ctx = Depends(current_admin)) -> Ctx:
        if perm not in ctx.perms:
            raise HTTPException(403, "permission denied")
        return ctx
    return dep


async def audit(s: AsyncSession, ctx: Ctx | None, action: str, target_type: str | None = None, target_id=None,
                prev=None, new=None, reason: str | None = None, admin_id=None, ip: str | None = None) -> None:
    s.add(AdminLog(admin_id=admin_id or (ctx.admin.id if ctx else None), action=action, target_type=target_type,
                   target_id=str(target_id) if target_id is not None else None, previous_value=prev, new_value=new,
                   reason=reason, ip_address=ip or (ctx.ip if ctx else None)))
