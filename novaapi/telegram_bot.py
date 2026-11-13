"""CryptoNOVA bot on aiogram 3, webhook mode (serverless). Holds no user secrets."""
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, Update, WebAppInfo)
from fastapi import HTTPException
from novaapi.api.v1.routes import bot_summary
from novaapi.core.config import app_url, settings
from novaapi.core.db import SessionLocal
from novaapi.services import notifier
from novaapi.services import wallet as wsvc

dp = Dispatcher()
WELCOME = ("Welcome to CryptoNOVA.\n\nYour digital portfolio starts here.\n\n"
           "Explore virtual assets, manage your wallet and transfer tokens inside the CryptoNOVA ecosystem.\n\n"
           "⚠️ Educational simulator: all assets are virtual (DEMO).")
HELP = ("CryptoNOVA — educational crypto simulator. No real money, no blockchain.\n\n"
        "/app open Mini App · /wallet balances · /assets prices · /history operations · /profile · /support")
COMMANDS = [("start", "Start"), ("app", "Open Mini App"), ("wallet", "My wallet"), ("assets", "Assets"), ("history", "History"),
            ("profile", "Profile"), ("help", "Help"), ("support", "Support")]


def kb() -> InlineKeyboardMarkup:
    rows = []
    if app_url():
        rows.append([InlineKeyboardButton(text="Open CryptoNOVA", web_app=WebAppInfo(url=app_url()))])
    rows.append([InlineKeyboardButton(text="My Wallet", callback_data="wallet"), InlineKeyboardButton(text="Help", callback_data="help")])
    rows.append([InlineKeyboardButton(text="Support", callback_data="support")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def summary(tg_id: int):
    async with SessionLocal() as s:
        try:
            return await bot_summary(tg_id, s)
        except HTTPException:
            return None


def wallet_text(d: dict) -> str:
    p = d["portfolio"]
    return "\n".join([f"💼 Wallet {p['wallet_id']} (DEMO)", f"Total: {float(p['total_value']):,.2f} NUSD-equivalent", ""] + [f"{a['symbol']}: {a['amount']}" for a in p["assets"]])


@dp.message(CommandStart())
async def start(m: Message):
    u = m.from_user
    async with SessionLocal() as s:
        user, _ = await wsvc.get_or_create_user(s, {"id": u.id, "username": u.username, "first_name": u.first_name})
        await s.commit()
        uid = user.id
    await m.answer(WELCOME, reply_markup=kb())
    async with SessionLocal() as s:
        await notifier.deliver(s, limit=5, user_ids=[uid])


@dp.message(Command("app"))
async def app_cmd(m: Message):
    await m.answer("Open CryptoNOVA:", reply_markup=kb())


@dp.message(Command("wallet"))
async def wallet(m: Message):
    d = await summary(m.from_user.id)
    await m.answer(wallet_text(d) if d else "Send /start first.")


@dp.callback_query(F.data == "wallet")
async def wallet_cb(c: CallbackQuery):
    d = await summary(c.from_user.id)
    await c.message.answer(wallet_text(d) if d else "Send /start first."); await c.answer()


@dp.message(Command("assets"))
async def assets(m: Message):
    d = await summary(m.from_user.id)
    await m.answer("\n".join(f"{a['symbol']} — {a['name']}: {a['price']} (DEMO)" for a in d["portfolio"]["assets"]) if d else "Send /start first.")


@dp.message(Command("history"))
async def history(m: Message):
    d = await summary(m.from_user.id)
    if not d:
        return await m.answer("Send /start first.")
    await m.answer("\n".join(f"{h['sign']}{h['amount']} {h['symbol']} · {h['type']}" for h in d["history"]) or "No operations yet.")


@dp.message(Command("profile"))
async def profile(m: Message):
    d = await summary(m.from_user.id)
    if not d:
        return await m.answer("Send /start first.")
    u = d["user"]
    await m.answer(f"👤 @{u['username']}\nTelegram ID: {u['telegram_id']}\nInternal ID: {u['id']}\nRegistered: {u['registered_at'][:10]}")


@dp.message(Command("help"))
async def help_(m: Message):
    await m.answer(HELP)


@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await c.message.answer(HELP); await c.answer()


@dp.message(Command("support"))
async def support(m: Message):
    await m.answer("Support: open the Mini App → Profile → Support and describe your issue.")


@dp.callback_query(F.data == "support")
async def support_cb(c: CallbackQuery):
    await c.message.answer("Support: open the Mini App → Profile → Support and describe your issue."); await c.answer()


async def process_update(data: dict) -> None:
    bot = Bot(settings.bot_token)
    try:
        await dp.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    except Exception:
        logging.exception("update failed")
    finally:
        await bot.session.close()


async def setup_webhook(base_url: str) -> dict:
    bot = Bot(settings.bot_token)
    try:
        await bot.set_webhook(url=f"{base_url}/api/v1/telegram/webhook", secret_token=settings.webhook_secret,
                              allowed_updates=["message", "callback_query"], drop_pending_updates=True)
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS])
        if app_url():
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Open CryptoNOVA", web_app=WebAppInfo(url=app_url())))
        info = await bot.get_webhook_info()
        return {"webhook": info.url, "pending": info.pending_update_count, "menu_button": bool(app_url())}
    finally:
        await bot.session.close()
