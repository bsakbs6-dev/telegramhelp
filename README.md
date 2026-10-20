# 📚 Telegram OCR Lecture & Notes Bot (Production Deployment)

Умный Telegram-бот на базе **Google Gemini AI** (`gemini-3.5-flash` / `gemini-3.1-flash-lite`) для автоматического распознавания конспектов, определения границ лекций (начала и конца темы) и экспорта в оформленный **PDF** или текстовые сообщения.

---

## 📁 Структура проекта

```text
├── handlers/              # Обработчики команд, сообщений и фото
│   ├── admin.py           # Админ-панель, генерация ключей, бан/разбан
│   ├── common.py          # /start, /help, /register
│   └── ocr.py             # Буферизация фото (альбомы), Gemini OCR, экспорт
├── services/
│   ├── ocr_service.py     # Интеграция с Gemini 3.5 Flash / 3.1 Flash Lite
│   └── pdf_service.py     # Кроссплатформенный генератор PDF (Cyrillic TrueType)
├── .env.example           # Шаблон конфигурации
├── .gitignore             # Исключение лишних файлов (базы, временные файлы)
├── bot.service            # Шаблон systemd-сервиса для Linux
├── config.py              # Загрузка настроек из переменных окружения
├── database.py            # SQLite база данных пользователей и ключей
├── deploy.sh              # Скрипт автоматической установки для Ubuntu/Debian
├── Dockerfile             # Docker-образ со встроенными шрифтами кириллицы
├── docker-compose.yml     # Запуск в Docker в 1 команду
├── keyboards.py           # Инлайн-клавиатуры
├── main.py                # Точка входа (aiogram 3)
└── requirements.txt       # Зависимости Python
```

---

## 🚀 Вариант 1: Выгрузка проекта на GitHub

1. Инициализируйте Git в этой папке:
   ```bash
   git init
   git branch -M main
   ```
2. Создайте новый репозиторий на [GitHub](https://github.com/new) (например, `telegram-ocr-bot`).
3. Добавьте файлы и отправьте код в репозиторий:
   ```bash
   git add .
   git commit -m "Initial commit: Telegram OCR Lecture Bot"
   git remote add origin https://github.com/ВАШ_НИК/ВАШ_РЕПОЗИТОРИЙ.git
   git push -u origin main
   ```
> ⚠️ **Важно:** Файл `.env` с секретными ключами уже добавлен в `.gitignore` и не попадёт в открытый доступ на GitHub.

---

## 🌐 Вариант 2: Развертывание на постоянном сервере (VPS)

### Способ A: Через Docker Compose (Рекомендуемый ⭐️)

Самый надёжный способ: не требует настройки Python и гарантирует идеальную работу шрифтов PDF.

1. Склонируйте репозиторий на сервере:
   ```bash
   git clone https://github.com/ВАШ_НИК/ВАШ_РЕПОЗИТОРИЙ.git
   cd ВАШ_РЕПОЗИТОРИЙ
   ```
2. Создайте файл `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
   *(Укажите ваши `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID`)*
3. Запустите бота в фоне:
   ```bash
   docker compose up -d --build
   ```
4. Управление:
   - Просмотр логов: `docker compose logs -f`
   - Перезапуск: `docker compose restart`
   - Остановка: `docker compose down`

---

### Способ B: Классическая установка на Ubuntu / Debian (systemd)

1. Запустите скрипт автоустановки:
   ```bash
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```
2. Заполните `.env`:
   ```bash
   nano .env
   ```
3. Для автозапуска после перезагрузки сервера:
   ```bash
   sudo cp bot.service /etc/systemd/system/
   # Отредактируйте путь к папке в /etc/systemd/system/bot.service если проект лежит не в /opt/telegram-ocr-bot
   sudo systemctl daemon-reload
   sudo systemctl enable bot
   sudo systemctl start bot
   ```
4. Статус и логи службы:
   ```bash
   sudo systemctl status bot
   sudo journalctl -u bot -f
   ```

---

## 🔑 Управление доступом (Админка)

- **ID Администратора:** `7061799104` (уже имеет полный доступ без ключей).
- **Команда `/admin`:**
  - `➕ Сгенерировать ключ` — создаёт одноразовый ключ доступа вида `KEY-XXXXXXXXXX`.
  - `📋 Список ключей` — просмотр доступных и использованных ключей.
  - `👥 Пользователи` — просмотр всех участников с кнопками моментального бана/разбана.
  - `📊 Статистика` — сводка по обработанным страницам и запросам.
- **Команда `/genkey`:** быстрая генерация ключа в чате.
