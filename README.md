# CryptoNOVA — Your Digital Assets. Your Universe.
Учебный симулятор криптобиржи: Telegram-бот + Mini App (`/`) + админка (`/admin`). Все активы виртуальные (DEMO).

## Запуск на Vercel
1. Загрузите ВСЕ файлы этой папки в репозиторий GitHub (одним перетаскиванием, их меньше 100).
2. Vercel -> Add New -> Project -> выберите репозиторий. Application Preset: **Next.js**, Root Directory: `./`.
3. Environment Variables: добавьте ОДИН ключ `BOT_TOKEN` (токен от @BotFather). Нажмите Deploy.
4. Storage -> Create Database -> **Neon** -> Connect (DATABASE_URL добавится сам). Затем Deployments -> Redeploy.
5. Откройте `https://<проект>.vercel.app/health` — должно быть `"db":"ready"`.
6. Откройте `https://<проект>.vercel.app/admin` — мастер первого запуска создаст владельца (BOT_TOKEN, email, пароль, QR для аутентификатора).

Если что-то не так, `/health` покажет причину (`hint`) и недостающие переменные (`missing_env`).
В КОРНЕ репозитория должны лежать: `package.json`, `vercel.json`, `requirements.txt` и папки `api`, `app`, `novaapi`.
