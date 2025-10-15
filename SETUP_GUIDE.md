# Инструкция по настройке VK Payment Bot

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 2. Настройка переменных окружения (.env)

Создайте файл `.env` в корневой папке проекта:

```env
# VK API
VK_GROUP_TOKEN=ваш_токен_группы
VK_CONFIRMATION_TOKEN=ваш_токен_подтверждения

# YooKassa
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_secret_key

# Сервер
BASE_URL=https://ваш_домен.com
PRIVATE_GROUP_URL=https://vk.com/club123456789

# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=ваш_пароль
PG_DBNAME=vk_bot_db

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

## 3. Подготовка VK сообщества

1. Откройте сообщество в ВК
2. Перейдите в **Управление → API → Longpoll API**
3. Включите "Прием событий"
4. Перейдите в **Управление → API → Callback API**
5. Установите версию API (например, 5.131)
6. Добавьте адрес сервера: `https://ваш_домен.com/vk_callback`
7. Выберите события:
   - `message_new` — новые сообщения
8. Получите и сохраните **Confirmation token**
9. Создайте токен доступа сообщества (сохраните как `VK_GROUP_TOKEN`)

## 4. Подготовка YooKassa

1. Зарегистрируйтесь на [yookassa.ru](https://yookassa.ru)
2. Создайте магазин (shop)
3. Получите **Shop ID** и **Secret Key**
4. Перейдите в **Настройки → Webhook'и**
5. Добавьте webhook: `https://ваш_домен.com/yookassa_webhook`
6. Выберите события: `payment.succeeded`

## 5. Создание базы данных PostgreSQL

```bash
createdb vk_bot_db
```

Или выполните SQL команду:
```sql
CREATE DATABASE vk_bot_db;
```

## 6. Запуск бота

```bash
python main.py
```

Бот запустится на `http://0.0.0.0:5000`

## 7. Использование HTTPS (ngrok или проксирование)

Для локального тестирования используйте ngrok:

```bash
ngrok http 5000
```

Скопируйте HTTPS URL и используйте его как `BASE_URL` в `.env`

## Поток взаимодействия

1. Пользователь пишет "начать" или "привет" → бот приветствует
2. Пользователь пишет "купить" → бот просит email
3. Пользователь отправляет email → бот создает платеж и отправляет ссылку
4. Пользователь оплачивает → YooKassa отправляет webhook
5. Бот получает webhook → подтверждает оплату в БД → отправляет ссылку на группу
6. Пользователь пишет "доступ" → бот выдает ссылку на группу
7. Пользователь пишет "статус" → бот проверяет статус оплаты

## Структура проекта

```
vk-payment-bot/
├── main.py                 # Основной файл Flask приложения
├── config.py              # Конфигурация (переменные окружения)
├── requirements.txt       # Зависимости Python
├── .env                   # Переменные окружения (НЕ коммитить!)
├── .gitignore            # Игнорируемые файлы
├── handlers/
│   ├── __init__.py
│   ├── start_handler.py    # Обработчик команды "начать"
│   ├── payment_handler.py  # Обработчик оплаты
│   └── access_handler.py   # Обработчик команды "доступ"
├── utils/
│   ├── __init__.py
│   ├── db.py              # Работа с PostgreSQL
│   ├── vk_api_wrapper.py  # Обёртка VK API
│   └── yookassa_api.py    # Работа с YooKassa
└── static/
    └── messages.json      # Сообщения бота
```

## Команды бота для пользователей

- `начать` или `привет` — приветствие
- `купить` — начать процесс покупки
- `статус` — проверить статус оплаты
- `доступ` — получить ссылку на группу (после оплаты)
- `E-mail адрес` — отправить email для оплаты
