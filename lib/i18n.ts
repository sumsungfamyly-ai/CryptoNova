// Interface language (ru / en). English is the source language of every string in the UI; Russian is applied by translating
// the rendered DOM (text nodes + placeholder/title/aria-label), so components do not need to be changed. Unknown text stays English.
export type Lang = "en" | "ru";
const KEY = "nova_lang";

const RU: Record<string, string> = {
 "Home": "Главная",
 "Markets": "Рынок",
 "Wallet": "Кошелёк",
 "Activity": "История",
 "Profile": "Профиль",
 "Hello,": "Привет,",
 "there": "друг",
 "Send": "Отправить",
 "Receive": "Получить",
 "Swap": "Обмен",
 "Assets": "Активы",
 "Settings": "Настройки",
 "Support": "Поддержка",
 "Continue": "Продолжить",
 "Done": "Готово",
 "Cancel": "Отмена",
 "Confirm": "Подтвердить",
 "Close": "Закрыть",
 "Edit": "Изменить",
 "Max": "Макс.",
 "Share": "Поделиться",
 "Try again": "Повторить",
 "Hide": "Скрыть",
 "None": "Нет",
 "Total": "Итого",
 "Fee": "Комиссия",
 "To": "Кому",
 "From": "От кого",
 "Time": "Время",
 "Type": "Тип",
 "Status": "Статус",
 "Amount": "Сумма",
 "Price": "Цена",
 "Name": "Название",
 "Description": "Описание",
 "Message": "Сообщение",
 "Reason": "Причина",
 "Action": "Действие",
 "Actions": "Действия",
 "Role": "Роль",
 "Email": "Email",
 "Password": "Пароль",
 "User": "Пользователь",
 "Users": "Пользователи",
 "Asset": "Актив",
 "Symbol": "Символ",
 "Balance": "Баланс",
 "System": "Система",
 "All": "Все",
 "ALL": "Все",
 "Received": "Получено",
 "Sent": "Отправлено",
 "Swaps": "Обмены",
 "Admin Adjustment": "Корректировки",
 "Token Issuance": "Выпуск токенов",
 "Newest": "Сначала новые",
 "Oldest": "Сначала старые",
 "Total virtual balance": "Общий виртуальный баланс",
 "24h · current holdings": "24ч · текущие активы",
 "Your assets": "Ваши активы",
 "Recent activity": "Последние операции",
 "No activity yet": "Операций пока нет",
 "Send or receive tokens to see it here.": "Отправьте или получите токены, и они появятся здесь.",
 "Demonstration prices of virtual assets — not real quotes.": "Демонстрационные цены виртуальных активов — не реальные котировки.",
 "Search assets": "Поиск активов",
 "All Assets": "Все активы",
 "★ Watchlist": "★ Избранное",
 "Popular": "Популярные",
 "Stable Assets": "Стабильные",
 "Nova Ecosystem": "Экосистема Nova",
 "· cap": "· капитализация",
 "No assets found": "Активы не найдены",
 "Your watchlist is empty": "Избранное пусто",
 "Tap the star on an asset to follow it.": "Нажмите на звёздочку у актива, чтобы добавить его.",
 "Total virtual value": "Общая виртуальная стоимость",
 "This wallet is frozen. Transfers are unavailable.": "Кошелёк заморожен. Переводы недоступны.",
 "Available": "Доступно",
 "History": "История",
 "No operations yet": "Операций пока нет",
 "Search by asset or ID": "Поиск по активу или ID",
 "Nothing here": "Здесь пусто",
 "Try another filter.": "Попробуйте другой фильтр.",
 "Admin credit": "Начисление админом",
 "Admin debit": "Списание админом",
 "Token issuance": "Выпуск токенов",
 "Starting balance": "Стартовый баланс",
 "Swap (received)": "Обмен (получено)",
 "Swap (paid)": "Обмен (отдано)",
 "Username": "Имя пользователя",
 "Internal ID": "Внутренний ID",
 "User ID": "ID пользователя",
 "Wallet ID": "ID кошелька",
 "Registered": "Дата регистрации",
 "Operations": "Операций",
 "Dark theme": "Тёмная тема",
 "Language": "Язык",
 "Transfer notifications": "Уведомления о переводах",
 "Announcements": "Объявления",
 "Critical system notices are always delivered.": "Важные системные уведомления приходят всегда.",
 "Describe your issue": "Опишите проблему",
 "Send to support": "Отправить в поддержку",
 "Sent ✓": "Отправлено ✓",
 "CryptoNOVA is an educational simulator. All assets are virtual.": "CryptoNOVA — учебный симулятор. Все активы виртуальные.",
 "Your balance": "Ваш баланс",
 "Copy ID": "Скопировать ID",
 "Internal CryptoNOVA link — not a blockchain address": "Внутренняя ссылка CryptoNOVA — это не блокчейн-адрес",
 "@username or internal ID": "@username или внутренний ID",
 "Recent": "Недавние",
 "Review": "Проверить",
 "Confirm transfer": "Подтвердить перевод",
 "You send": "Вы отправляете",
 "Virtual transfer inside CryptoNOVA (DEMO). No real assets move.": "Виртуальный перевод внутри CryptoNOVA (DEMO). Реальные активы не перемещаются.",
 "You pay": "Вы платите",
 "You receive (estimate)": "Вы получите (оценка)",
 "Confirm swap": "Подтвердить обмен",
 "Swapped": "Обмен выполнен",
 "Virtual exchange at demo prices. Min. received is protected (1% tolerance).": "Виртуальный обмен по демо-ценам. Минимальная сумма получения защищена (допуск 1%).",
 "· fee": "· комиссия",
 ") · DEMO prices": ") · демо-цены",
 "Not enough data yet": "Данных пока недостаточно",
 "The chart fills in as prices are recorded.": "График заполнится по мере записи цен.",
 "Please open CryptoNOVA from Telegram.": "Откройте CryptoNOVA из Telegram.",
 "Could not sign in. Please reopen the app.": "Не удалось войти. Откройте приложение заново.",
 "Enter an amount": "Введите сумму",
 "Insufficient balance": "Недостаточно средств",
 "Recipient not found": "Получатель не найден",
 "recipient not found": "Получатель не найден",
 "Cannot send to yourself": "Нельзя отправить самому себе",
 "Recipient unavailable": "Получатель недоступен",
 "Wallet is frozen": "Кошелёк заморожен",
 "Asset not available": "Актив недоступен",
 "Amount must be positive": "Сумма должна быть больше нуля",
 "Maximum transfer amount exceeded": "Превышена максимальная сумма перевода",
 "Daily transfer limit exceeded": "Превышен дневной лимит переводов",
 "Account restricted": "Аккаунт ограничен",
 "Idempotency key required": "Нужен уникальный ключ операции",
 "Request failed": "Ошибка запроса",
 "Choose two different active assets": "Выберите два разных активных актива",
 "Price unavailable": "Цена недоступна",
 "Amount too small": "Слишком маленькая сумма",
 "Amount too small for this pair": "Слишком маленькая сумма для этой пары",
 "Price changed, please review the new quote": "Цена изменилась, проверьте новую котировку",
 "Target asset supply limit reached": "Достигнут лимит выпуска целевого актива",
 "invalid credentials": "Неверные данные для входа",
 "too many attempts, try later": "Слишком много попыток, попробуйте позже",
 "wrong bot token": "Неверный токен бота",
 "Wrong bot token": "Неверный токен бота",
 "owner already exists": "Владелец уже создан",
 "session expired, start again": "Сессия истекла, начните заново",
 "wrong code": "Неверный код",
 "confirmation required": "Требуется подтверждение",
 "permission denied": "Недостаточно прав",
 "not authenticated": "Нужно войти",
 "session expired": "Сессия истекла",
 "account disabled": "Аккаунт отключён",
 "bad CSRF token": "Недействительный токен защиты",
 "symbol already exists": "Такой символ уже существует",
 "max supply exceeded": "Превышен максимальный выпуск",
 "wallet or asset not found": "Кошелёк или актив не найден",
 "active": "активен",
 "blocked": "заблокирован",
 "frozen": "заморожен",
 "completed": "выполнено",
 "pending": "в ожидании",
 "cancelled": "отменено",
 "failed": "ошибка",
 "disabled": "отключён",
 "sent": "отправлено",
 "skipped": "пропущено",
 "on": "вкл",
 "off": "выкл",
 "OWNER": "ВЛАДЕЛЕЦ",
 "SUPER_ADMIN": "СУПЕР-АДМИН",
 "ADMIN": "АДМИН",
 "MODERATOR": "МОДЕРАТОР",
 "SUPPORT": "ПОДДЕРЖКА",
 "Dashboard": "Дашборд",
 "Wallets": "Кошельки",
 "Transactions": "Транзакции",
 "Token Management": "Управление токенами",
 "Issuance": "Выпуск",
 "Notifications": "Уведомления",
 "Administrators": "Администраторы",
 "Audit Logs": "Журнал аудита",
 "Sign in": "Войти",
 "Sign out": "Выйти",
 "Admin": "Админ",
 "Setup": "Настройка",
 "6-digit code": "6-значный код",
 "6-digit code (leave empty if you skipped MFA)": "6-значный код (оставьте пустым, если MFA пропущен)",
 "First launch: create the owner account. Paste the bot token from @BotFather to confirm you are the owner of this deployment.": "Первый запуск: создайте аккаунт владельца. Вставьте токен бота из @BotFather, чтобы подтвердить, что вы владелец этой установки.",
 "Bot token (from @BotFather)": "Токен бота (от @BotFather)",
 "Your email": "Ваш email",
 "Password (12+ characters)": "Пароль (от 12 символов)",
 "Skip the authenticator app": "Не использовать приложение-аутентификатор",
 "(less secure: you will sign in with the password only, so use a long one)": "(менее безопасно: вход только по паролю, поэтому используйте длинный)",
 "Enter a valid email": "Введите корректный email",
 "Password must be at least 12 characters": "Пароль должен быть не короче 12 символов",
 "Scan this QR code in Google Authenticator / Authy (or enter the key manually), then type the 6-digit code.": "Отсканируйте QR-код в Google Authenticator / Authy (или введите ключ вручную), затем введите 6-значный код.",
 "Create owner": "Создать владельца",
 "Owner created": "Владелец создан",
 "Go to sign in": "Перейти ко входу",
 "Enter": "Ввести",
 "Today": "Сегодня",
 "7 Days": "7 дней",
 "30 Days": "30 дней",
 "90 Days": "90 дней",
 "All Time": "За всё время",
 "Total Users": "Всего пользователей",
 "Active Users": "Активные пользователи",
 "Total Wallets": "Всего кошельков",
 "Virtual Supply (value)": "Виртуальное предложение (стоимость)",
 "Daily Transfers": "Переводов за сегодня",
 "New Registrations": "Новые регистрации",
 "Transfer Volume": "Объём переводов",
 "User Growth": "Рост пользователей",
 "Transaction Activity": "Активность транзакций",
 "Asset Distribution (value)": "Распределение активов (стоимость)",
 "Virtual Supply": "Виртуальное предложение",
 "All figures are computed from PostgreSQL. Virtual (DEMO) units only.": "Все показатели считаются по данным PostgreSQL. Только виртуальные (DEMO) единицы.",
 "Search username / ID": "Поиск: имя / ID",
 "All statuses": "Все статусы",
 "Telegram ID": "Telegram ID",
 "Tx": "Опер.",
 "Block": "Заблокировать",
 "Unblock": "Разблокировать",
 "Add note": "Добавить заметку",
 "Block user": "Блокировка пользователя",
 "Unblock user": "Разблокировка пользователя",
 "Edit note": "Редактировать заметку",
 "Note": "Заметка",
 "· Note:": "· Заметка:",
 "Search wallet ID / username": "Поиск: ID кошелька / имя",
 "Adjust": "Корректировка",
 "Freeze": "Заморозить",
 "Unfreeze": "Разморозить",
 "Freeze wallet": "Заморозка кошелька",
 "Unfreeze wallet": "Разморозка кошелька",
 "Adjust balance (DEMO)": "Корректировка баланса (DEMO)",
 "Symbol (e.g. NUSD)": "Символ (например, NUSD)",
 "Reason (required, saved to audit log)": "Причина (обязательно, сохраняется в журнале аудита)",
 "I confirm this action": "Я подтверждаю это действие",
 "+ New asset": "+ Новый актив",
 "Create virtual asset": "Создать виртуальный актив",
 "Symbol (A-Z0-9)": "Символ (A-Z, 0-9)",
 "Virtual price": "Виртуальная цена",
 "Max supply (empty = unlimited)": "Макс. выпуск (пусто = без лимита)",
 "Max supply": "Макс. выпуск",
 "Icon URL": "URL иконки",
 "Supply": "Выпуск",
 "Activate": "Включить",
 "Deactivate": "Выключить",
 "Distribution": "Распределение",
 "holders": "держатели",
 "Search asset / ID": "Поиск: актив / ID",
 "Export CSV": "Экспорт CSV",
 "All types": "Все типы",
 "Issue tokens": "Выпустить токены",
 "Issue virtual tokens": "Выпуск виртуальных токенов",
 "Wallet ID (NW-…)": "ID кошелька (NW-…)",
 "Send announcement": "Отправить объявление",
 "Maintenance notice (critical)": "Уведомление о тех. работах (критичное)",
 "Deliver pending now": "Доставить очередь сейчас",
 "Outbox status": "Статус очереди",
 "Announcement (users who enabled announcements)": "Объявление (для тех, кто включил объявления)",
 "Maintenance notice (all users)": "Уведомление о тех. работах (всем)",
 "+ New admin": "+ Новый админ",
 "Create administrator": "Создать администратора",
 "Password (min 12)": "Пароль (мин. 12 символов)",
 "Give this TOTP secret to the new admin (shown once)": "Передайте этот TOTP-ключ новому админу (показывается один раз)",
 "MFA": "MFA",
 "Last login": "Последний вход",
 "Change role": "Смена роли",
 "Toggle status": "Смена статуса",
 "Disable": "Отключить",
 "Enable": "Включить",
 "Filter by action (e.g. wallet_credit)": "Фильтр по действию (например, wallet_credit)",
 "Target": "Объект",
 "Previous": "Было",
 "New": "Стало",
 "The audit log is append-only; the database rejects edits and deletes.": "Журнал аудита только дополняется: база данных не позволяет изменять и удалять записи.",
 "JSON value": "Значение JSON",
 "No data": "Нет данных",
 "Outbox": "Очередь"
};

const PATTERNS: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^No (\S+) operations$/, (m) => `Нет операций ${m[1]}`],
  [/^Edit (.+)$/, (m) => `Изменить ${m[1]}`],
  [/^Activate (.+)$/, (m) => `Включить ${m[1]}`],
  [/^Deactivate (.+)$/, (m) => `Выключить ${m[1]}`],
  [/^Delivered (\d+), pending (\d+)$/, (m) => `Доставлено ${m[1]}, в очереди ${m[2]}`],
];

export function translate(s: string, l: Lang = "ru"): string {
  if (l !== "ru") return s;
  const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
  if (!m || !m[2]) return s;
  const hit = RU[m[2]];
  if (hit) return m[1] + hit + m[3];
  for (const [re, fn] of PATTERNS) {
    const x = m[2].match(re);
    if (x) return m[1] + fn(x) + m[3];
  }
  return s;
}

let lang: Lang = "en";
let obs: MutationObserver | null = null;
const listeners = new Set<(l: Lang) => void>();
const textOrig = new WeakMap<Text, { src: string; out: string }>();
const attrOrig = new WeakMap<Element, Record<string, { src: string; out: string }>>();
const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE"]);
const ATTRS = ["placeholder", "title", "aria-label"];
const CONFIG: MutationObserverInit = { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS };

function skipText(n: Text): boolean {
  const p = n.parentElement;
  if (!p || SKIP.has(p.tagName)) return true;
  return p.tagName === "OPTION" && !p.hasAttribute("value"); // option text is its value when no value attribute: keep it English
}

function trText(n: Text) {
  if (lang !== "ru" || skipText(n)) return;
  const v = n.nodeValue || "";
  const rec = textOrig.get(n);
  if (rec && rec.out === v) return;
  const out = translate(v, "ru");
  if (out !== v) { textOrig.set(n, { src: v, out }); n.nodeValue = out; }
}

function trAttrs(el: Element) {
  if (lang !== "ru") return;
  for (const a of ATTRS) {
    const v = el.getAttribute(a);
    if (v == null) continue;
    const rec = attrOrig.get(el)?.[a];
    if (rec && rec.out === v) continue;
    const out = translate(v, "ru");
    if (out !== v) {
      const m = attrOrig.get(el) || {};
      m[a] = { src: v, out };
      attrOrig.set(el, m);
      el.setAttribute(a, out);
    }
  }
}

function walk(root: Node) {
  if (root.nodeType === 3) return trText(root as Text);
  if (root.nodeType !== 1) return;
  const el = root as Element;
  if (SKIP.has(el.tagName)) return;
  trAttrs(el);
  for (let c = el.firstChild; c; c = c.nextSibling) walk(c);
}

function restore(root: Node) {
  if (root.nodeType === 3) {
    const t = root as Text;
    const rec = textOrig.get(t);
    if (rec && rec.out === t.nodeValue) t.nodeValue = rec.src;
    return;
  }
  if (root.nodeType !== 1) return;
  const el = root as Element;
  const m = attrOrig.get(el);
  if (m) for (const a in m) if (el.getAttribute(a) === m[a].out) el.setAttribute(a, m[a].src);
  el.childNodes.forEach(restore);
}

function start() {
  if (obs || typeof MutationObserver === "undefined") return;
  const o = new MutationObserver((muts) => {
    o.disconnect(); // our own edits must not re-trigger the observer
    try {
      for (const m of muts) {
        if (m.type === "characterData") trText(m.target as Text);
        else if (m.type === "attributes") trAttrs(m.target as Element);
        else m.addedNodes.forEach(walk);
      }
    } catch { /* never break the page because of translation */ }
    if (obs === o) o.observe(document.body, CONFIG);
  });
  obs = o;
  try { walk(document.body); } catch { /* ignore */ }
  o.observe(document.body, CONFIG);
}

function stop() {
  obs?.disconnect();
  obs = null;
  try { restore(document.body); } catch { /* ignore */ }
}

export const getLang = (): Lang => lang;

export function subscribe(fn: (l: Lang) => void): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

export function setLang(l: Lang, persist = true) {
  lang = l;
  if (persist) { try { localStorage.setItem(KEY, l); } catch { /* ignore */ } }
  if (typeof document !== "undefined") {
    document.documentElement.lang = l;
    if (l === "ru") start(); else stop();
  }
  listeners.forEach((f) => f(l));
}

export function initLang() {
  let l: Lang = "en";
  try {
    const s = localStorage.getItem(KEY);
    l = s === "ru" || s === "en" ? s : (navigator.language || "").toLowerCase().startsWith("ru") ? "ru" : "en";
  } catch { /* ignore */ }
  setLang(l, false);
}
