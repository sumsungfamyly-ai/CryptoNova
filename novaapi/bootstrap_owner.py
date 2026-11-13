"""Create the OWNER account (TOTP mandatory). CLI: python -m novaapi.bootstrap_owner"""
import asyncio
from sqlalchemy import select
from novaapi.core.config import settings
from novaapi.core.db import SessionLocal
from novaapi.models import Admin, AdminRole
from novaapi.security.passwords import hash_password, new_totp_secret


async def create_owner() -> dict:
    if not settings.owner_bootstrap_email or len(settings.owner_bootstrap_password) < 12:
        return {"status": "skipped", "reason": "set OWNER_BOOTSTRAP_EMAIL and OWNER_BOOTSTRAP_PASSWORD (>=12 chars)"}
    async with SessionLocal() as s, s.begin():
        if (await s.execute(select(Admin).where(Admin.email == settings.owner_bootstrap_email.lower()))).scalar_one_or_none():
            return {"status": "exists"}
        role = (await s.execute(select(AdminRole).where(AdminRole.name == "OWNER"))).scalar_one()
        preset = bool(settings.owner_totp_secret)
        secret = settings.owner_totp_secret or new_totp_secret()
        s.add(Admin(email=settings.owner_bootstrap_email.lower(), password_hash=hash_password(settings.owner_bootstrap_password),
                    role_id=role.id, mfa_secret=secret, mfa_enabled=True))
    return {"status": "created", "otpauth": None if preset else f"otpauth://totp/CryptoNOVA:{settings.owner_bootstrap_email}?secret={secret}&issuer=CryptoNOVA"}


if __name__ == "__main__":
    print(asyncio.run(create_owner()))
