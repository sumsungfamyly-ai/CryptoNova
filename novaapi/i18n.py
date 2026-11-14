"""Bot / notification texts in Russian and English (pure data, no dependencies)."""

def lang_of(code) -> str:
    """Telegram language_code -> supported language."""
    return "ru" if str(code or "").lower().startswith("ru") else "en"


STR = {
    "en": {
        "welcome": ("Welcome to CryptoNOVA.\n\nYour digital portfolio starts here.\n\n"
                    "Explore virtual assets, manage your wallet and transfer tokens inside the CryptoNOVA ecosystem.\n\n"
                    "⚠️ Educational simulator: all assets are virtual (DEMO)."),
        "help": ("CryptoNOVA — educational crypto simulator. No real money, no blockchain.\n\n"
                 "/app open Mini App · /wallet balances · /assets prices · /history operations · /profile · /support · /language"),
        "open_prompt": "Open CryptoNOVA:",
        "btn_open": "Open CryptoNOVA", "btn_wallet": "My Wallet", "btn_help": "Help", "btn_support": "Support", "btn_lang": "🌐 Language",
        "start_first": "Send /start first.",
        "wallet_head": "💼 Wallet {id} (DEMO)",
        "wallet_total": "Total: {value} NUSD-equivalent",
        "no_ops": "No operations yet.",
        "profile": "👤 @{username}\nTelegram ID: {tg}\nInternal ID: {id}\nRegistered: {date}",
        "support": "Support: open the Mini App → Profile → Support and describe your issue.",
        "lang_prompt": "Choose your language / Выберите язык:",
        "lang_set": "Language set: English ✅",
    },
    "ru": {
        "welcome": ("Добро пожаловать в CryptoNOVA.\n\nВаш цифровой портфель начинается здесь.\n\n"
                    "Изучайте виртуальные активы, управляйте кошельком и переводите токены внутри экосистемы CryptoNOVA.\n\n"
                    "⚠️ Учебный симулятор: все активы виртуальные (DEMO)."),
        "help": ("CryptoNOVA — учебный симулятор криптобиржи. Без реальных денег и блокчейна.\n\n"
                 "/app открыть Mini App · /wallet балансы · /assets цены · /history операции · /profile профиль · /support поддержка · /language язык"),
        "open_prompt": "Открыть CryptoNOVA:",
        "btn_open": "Открыть CryptoNOVA", "btn_wallet": "Мой кошелёк", "btn_help": "Помощь", "btn_support": "Поддержка", "btn_lang": "🌐 Язык",
        "start_first": "Сначала отправьте /start.",
        "wallet_head": "💼 Кошелёк {id} (DEMO)",
        "wallet_total": "Итого: {value} в эквиваленте NUSD",
        "no_ops": "Операций пока нет.",
        "profile": "👤 @{username}\nTelegram ID: {tg}\nВнутренний ID: {id}\nДата регистрации: {date}",
        "support": "Поддержка: откройте Mini App → Профиль → Поддержка и опишите проблему.",
        "lang_prompt": "Choose your language / Выберите язык:",
        "lang_set": "Язык установлен: Русский ✅",
    },
}

TX = {
    "en": {"transfer": "transfer", "admin_credit": "admin credit", "admin_debit": "admin debit", "issuance": "issuance",
           "initial_grant": "starting balance", "swap_in": "swap (received)", "swap_out": "swap (paid)", "fee": "fee"},
    "ru": {"transfer": "перевод", "admin_credit": "начисление админом", "admin_debit": "списание админом", "issuance": "выпуск",
           "initial_grant": "стартовый баланс", "swap_in": "обмен (получено)", "swap_out": "обмен (отдано)", "fee": "комиссия"},
}

COMMANDS = {
    "en": [("start", "Start"), ("app", "Open Mini App"), ("wallet", "My wallet"), ("assets", "Assets"), ("history", "History"),
           ("profile", "Profile"), ("language", "Language"), ("help", "Help"), ("support", "Support")],
    "ru": [("start", "Начать"), ("app", "Открыть Mini App"), ("wallet", "Мой кошелёк"), ("assets", "Активы"), ("history", "История"),
           ("profile", "Профиль"), ("language", "Язык"), ("help", "Помощь"), ("support", "Поддержка")],
}

NOTIF = {
    "en": {
        "wallet_created": lambda p: f"✅ Wallet created: {p.get('wallet_id')}",
        "transfer_sent": lambda p: f"📤 Sent {p.get('amount')} {p.get('symbol')} to {p.get('to')}",
        "transfer_received": lambda p: f"📥 Received {p.get('amount')} {p.get('symbol')} from {p.get('from')}",
        "admin_announcement": lambda p: f"📢 {p.get('text', '')}",
        "account_restricted": lambda p: "⛔ Your account has been restricted.",
        "system_maintenance": lambda p: f"🛠 Maintenance: {p.get('text', '')}",
        "asset_created": lambda p: f"🆕 New virtual asset: {p.get('symbol')}",
        "_default": lambda p: "CryptoNOVA update",
    },
    "ru": {
        "wallet_created": lambda p: f"✅ Кошелёк создан: {p.get('wallet_id')}",
        "transfer_sent": lambda p: f"📤 Отправлено {p.get('amount')} {p.get('symbol')} → {p.get('to')}",
        "transfer_received": lambda p: f"📥 Получено {p.get('amount')} {p.get('symbol')} от {p.get('from')}",
        "admin_announcement": lambda p: f"📢 {p.get('text', '')}",
        "account_restricted": lambda p: "⛔ Ваш аккаунт ограничен.",
        "system_maintenance": lambda p: f"🛠 Технические работы: {p.get('text', '')}",
        "asset_created": lambda p: f"🆕 Новый виртуальный актив: {p.get('symbol')}",
        "_default": lambda p: "Обновление CryptoNOVA",
    },
}


def notif_text(lang: str, ntype: str, payload: dict) -> str:
    table = NOTIF.get(lang, NOTIF["en"])
    return table.get(ntype, table["_default"])(payload or {})
