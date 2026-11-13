from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.models import Notification, NotificationPreference

PREF_BY_TYPE = {"transfer_sent": "transfers", "transfer_received": "transfers", "admin_announcement": "announcements", "asset_created": "announcements"}


async def enqueue(s: AsyncSession, user_id, ntype: str, payload: dict, dedupe_key: str, critical: bool = False) -> None:
    if (await s.execute(select(Notification.id).where(Notification.dedupe_key == dedupe_key))).first():
        return  # already queued: no duplicates
    status = "pending"
    attr = PREF_BY_TYPE.get(ntype)
    if attr and not critical:
        pref = (await s.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))).scalar_one_or_none()
        if pref is not None and not getattr(pref, attr):
            status = "skipped"
    s.add(Notification(user_id=user_id, type=ntype, payload=payload, dedupe_key=dedupe_key,
                       is_critical=critical, status=status))
