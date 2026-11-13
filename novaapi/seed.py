"""Idempotent seed: roles/permissions, 5 DEMO assets, system treasury, settings.
Run: python -m novaapi.seed
Does NOT create users, balances or fake statistics (analytics use real data only)."""
import asyncio
import uuid
from decimal import Decimal
from sqlalchemy import select
from novaapi.core.config import settings
from novaapi.core.db import SessionLocal
from novaapi.models import Asset, AssetPrice, AdminPermission, AdminRole, Balance, Setting, User, Wallet

ROLES = {"OWNER": 0, "SUPER_ADMIN": 1, "ADMIN": 2, "MODERATOR": 3, "SUPPORT": 4}
ALL = ["users.view", "users.block", "users.note", "wallets.view", "wallets.adjust", "wallets.freeze",
       "assets.view", "assets.manage", "issuance.manage", "transactions.view", "notifications.send",
       "admins.manage", "logs.view", "settings.manage", "dashboard.view"]
PERMS = {
    "OWNER": ALL,
    "SUPER_ADMIN": [p for p in ALL if p != "admins.manage"] + [],
    "ADMIN": ["users.view", "users.block", "users.note", "wallets.view", "wallets.freeze", "assets.view",
              "assets.manage", "transactions.view", "dashboard.view", "logs.view"],
    "MODERATOR": ["users.view", "users.block", "users.note", "wallets.view", "wallets.freeze", "transactions.view"],
    "SUPPORT": ["users.view", "wallets.view", "transactions.view"],
}
ASSETS = [
    ("NUSD", "Nova Dollar", "Virtual stable unit pegged to 1.00 within the simulator.", "1", "stable", None),
    ("NBTC", "Nova Bitcoin", "Virtual scarce asset inspired by digital-asset concepts.", "43250", "popular", "21000000"),
    ("NETH", "Nova Ethereum", "Virtual smart-platform themed asset.", "2280", "popular", None),
    ("NOVA", "Nova Token", "Native token of the CryptoNOVA ecosystem.", "2.5", "nova", "1000000000"),
    ("NGOLD", "Nova Gold", "Virtual commodity-style unit. Not backed by real gold.", "62", "stable", None),
]
SYSTEM_TELEGRAM_ID = 0  # reserved id for the system treasury user


async def main() -> None:
    async with SessionLocal() as s, s.begin():
        roles = {}
        for name, rank in ROLES.items():
            r = (await s.execute(select(AdminRole).where(AdminRole.name == name))).scalar_one_or_none()
            if not r:
                r = AdminRole(name=name, rank=rank); s.add(r); await s.flush()
            roles[name] = r
            have = {p.permission for p in (await s.execute(
                select(AdminPermission).where(AdminPermission.role_id == r.id))).scalars()}
            s.add_all(AdminPermission(role_id=r.id, permission=p) for p in PERMS[name] if p not in have)

        assets = {}
        for sym, name, desc, price, cat, mx in ASSETS:
            a = (await s.execute(select(Asset).where(Asset.symbol == sym))).scalar_one_or_none()
            if not a:
                a = Asset(symbol=sym, name=name, description=desc, virtual_price=Decimal(price), category=cat,
                          max_supply=Decimal(mx) if mx else None, icon=f"/icons/{sym.lower()}.svg")
                s.add(a); await s.flush()
                s.add(AssetPrice(asset_id=a.id, price=a.virtual_price))
            assets[sym] = a

        sysu = (await s.execute(select(User).where(User.telegram_id == SYSTEM_TELEGRAM_ID))).scalar_one_or_none()
        if not sysu:
            sysu = User(telegram_id=SYSTEM_TELEGRAM_ID, username="nova_treasury", first_name="CryptoNOVA Treasury",
                        is_system=True)
            s.add(sysu); await s.flush()
            s.add(Wallet(user_id=sysu.id, public_id="NW-TREASURY"))
            await s.flush()
        wallet = (await s.execute(select(Wallet).where(Wallet.user_id == sysu.id))).scalar_one()
        for a in assets.values():
            if not (await s.execute(select(Balance).where(Balance.wallet_id == wallet.id,
                                                          Balance.asset_id == a.id))).scalar_one_or_none():
                s.add(Balance(wallet_id=wallet.id, asset_id=a.id, amount=Decimal(0), allow_negative=True))

        defaults = {"simulator_mode": {"value": settings.simulator_mode},
                    "transfer_fee": {"enabled": settings.transfer_fee_enabled, "percent": str(settings.transfer_fee_percent)},
                    "transfer_max_amount": {"value": str(settings.transfer_max_amount)},
                    "daily_limit": {"value": str(settings.daily_transfer_limit)},
                    "swap_fee": {"percent": str(settings.swap_fee_percent)},
                    "starting_balances": {k: str(v) for k, v in settings.parsed_starting_balances().items()}}
        for k, v in defaults.items():
            if not (await s.execute(select(Setting).where(Setting.key == k))).scalar_one_or_none():
                s.add(Setting(key=k, value=v))
    print("seed ok")


if __name__ == "__main__":
    asyncio.run(main())
