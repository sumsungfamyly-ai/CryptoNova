"""CryptoNOVA bot on aiogram 3, webhook mode (serverless). Bilingual: Russian / English. Holds no user secrets."""
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, Update, WebAppInfo)
from fastapi import HTTPException
from sqlalchemy import select
from novaapi.api.v1.routes import bot_summary
from novaapi.core.config import app_url, settings
from novaapi.core.db import SessionLocal
from novaapi.i18n import COMMANDS, STR, TX, lang_of
from novaapi.models import User
from novaapi.services import notifier
from novaapi.services import wallet as wsvc

dp = Dispatcher()


async def get_lang(u) -> str:
    """Saved language of the user, else the Telegram interface language."""
    async with SessionLocal() as s:
        saved = (await s.execute(select(User.language).where(User.telegram_id == u.id))).scalar_one_or_none()
    return saved or lang_of(getattr(u, "language_code", None))


def kb(lang: str) -> InlineKeyboardMarkup:
    t = STR[lang]
    rows = []
    if app_url():
        rows.append([InlineKeyboardButton(text=t["btn_open"], web_app=WebAppInfo(url=app_url()))])
    rows.append([InlineKeyboardButton(text=t["btn_wallet"], callback_data="wallet"), InlineKeyboardButton(text=t["btn_help"], callback_data="help")])
    rows.append([InlineKeyboardButton(text=t["btn_support"], callback_data="support"), InlineKeyboardButton(text=t["btn_lang"], callback_data="lang_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                                                  InlineKeyboardButton(text="English", callback_data="lang:en")]])


async def summary(tg_id: int):
    async with SessionLocal() as s:
        try:
            return await bot_summary(tg_id, s)
        except HTTPException:
            return None


def wallet_text(d: dict, lang: str) -> str:
    p, t = d["portfolio"], STR[lang]
    return "\n".join([t["wallet_head"].format(id=p["wallet_id"]), t["wallet_total"].format(value=f"{float(p['total_value']):,.2f}"), ""]
                     + [f"{a['symbol']}: {a['amount']}" for a in p["assets"]])


@dp.message(CommandStart())
async def start(m: Message):
    u = m.from_user
    async with SessionLocal() as s:
        user, _ = await wsvc.get_or_create_user(s, {"id": u.id, "username": u.username, "first_name": u.first_name, "language_code": u.language_code})
        await s.commit()
        uid, lang = user.id, user.language
    await m.answer(STR[lang]["welcome"], reply_markup=kb(lang))
    async with SessionLocal() as s:
        await notifier.deliver(s, limit=5, user_ids=[uid])


@dp.message(Command("app"))
async def app_cmd(m: Message):
    lang = await get_lang(m.from_user)
    await m.answer(STR[lang]["open_prompt"], reply_markup=kb(lang))


@dp.message(Command("wallet"))
async def wallet(m: Message):
    lang, d = await get_lang(m.from_user), await summary(m.from_user.id)
    await m.answer(wallet_text(d, lang) if d else STR[lang]["start_first"])


@dp.callback_query(F.data == "wallet")
async def wallet_cb(c: CallbackQuery):
    lang, d = await get_lang(c.from_user), await summary(c.from_user.id)
    await c.message.answer(wallet_text(d, lang) if d else STR[lang]["start_first"]); await c.answer()


@dp.message(Command("assets"))
async def assets(m: Message):
    lang, d = await get_lang(m.from_user), await summary(m.from_user.id)
    await m.answer("\n".join(f"{a['symbol']} — {a['name']}: {a['price']} (DEMO)" for a in d["portfolio"]["assets"]) if d else STR[lang]["start_first"])


@dp.message(Command("history"))
async def history(m: Message):
    lang, d = await get_lang(m.from_user), await summary(m.from_user.id)
    if not d:
        return await m.answer(STR[lang]["start_first"])
    await m.answer("\n".join(f"{h['sign']}{h['amount']} {h['symbol']} · {TX[lang].get(h['type'], h['type'])}" for h in d["history"]) or STR[lang]["no_ops"])


@dp.message(Command("profile"))
async def profile(m: Message):
    lang, d = await get_lang(m.from_user), await summary(m.from_user.id)
    if not d:
        return await m.answer(STR[lang]["start_first"])
    u = d["user"]
    await m.answer(STR[lang]["profile"].format(username=u["username"], tg=u["telegram_id"], id=u["id"], date=u["registered_at"][:10]))


@dp.message(Command("help"))
async def help_(m: Message):
    await m.answer(STR[await get_lang(m.from_user)]["help"])


@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await c.message.answer(STR[await get_lang(c.from_user)]["help"]); await c.answer()


@dp.message(Command("support"))
async def support(m: Message):
    await m.answer(STR[await get_lang(m.from_user)]["support"])


@dp.callback_query(F.data == "support")
async def support_cb(c: CallbackQuery):
    await c.message.answer(STR[await get_lang(c.from_user)]["support"]); await c.answer()


@dp.message(Command("language"))
async def language_cmd(m: Message):
    await m.answer(STR["en"]["lang_prompt"], reply_markup=lang_kb())


@dp.callback_query(F.data == "lang_menu")
async def lang_menu_cb(c: CallbackQuery):
    await c.message.answer(STR["en"]["lang_prompt"], reply_markup=lang_kb()); await c.answer()


@dp.callback_query(F.data.in_({"lang:ru", "lang:en"}))
async def lang_set_cb(c: CallbackQuery):
    new = c.data.split(":")[1]
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.telegram_id == c.from_user.id))).scalar_one_or_none()
        if u:
            u.language = new
            await s.commit()
    await c.message.answer(STR[new]["lang_set"], reply_markup=kb(new)); await c.answer()


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
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS["en"]])
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS["ru"]], language_code="ru")
        if app_url():
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="CryptoNOVA", web_app=WebAppInfo(url=app_url())))
        info = await bot.get_webhook_info()
        return {"webhook": info.url, "pending": info.pending_update_count, "menu_button": bool(app_url())}
    finally:
        await bot.session.close()
