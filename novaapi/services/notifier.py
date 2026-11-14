import asyncio
from datetime import datetime, timezone
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings
from novaapi.i18n import notif_text
from novaapi.models import Notification, User


async def _send(c: httpx.AsyncClient, chat_id: int, text: str) -> bool:
    r = await c.post(f"https://api.telegram.org/bot{settings.bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})
    return r.status_code == 200


async def deliver(s: AsyncSession, limit: int = 25, user_ids: list | None = None) -> dict:
    """Send pending outbox rows in the user's language (bounded per call so it fits a serverless request). Each row is sent at most once."""
    if not settings.bot_token:
        return {"sent": 0, "remaining": 0}
    st = (select(Notification, User.telegram_id, User.language).join(User, User.id == Notification.user_id)
          .where(Notification.status == "pending", User.is_system.is_(False)).order_by(Notification.created_at).limit(limit))
    if user_ids:
        st = st.where(Notification.user_id.in_(user_ids))
    rows = (await s.execute(st)).all()
    sent = 0
    if rows:
        async with httpx.AsyncClient(timeout=8) as c:
            res = await asyncio.gather(*[_send(c, tg, notif_text(lang, n.type, n.payload)) for n, tg, lang in rows], return_exceptions=True)
        now = datetime.now(timezone.utc)
        for (n, _, _), r in zip(rows, res):
            n.status, n.sent_at = ("sent" if r is True else "failed"), now
            sent += r is True
        await s.commit()
    remaining = (await s.execute(select(func.count()).select_from(Notification).where(Notification.status == "pending"))).scalar_one()
    return {"sent": sent, "remaining": remaining}
