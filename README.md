## Shop Bot

Telegram-бот для каталога товаров, корзины, заказов и админ-панели через команды.

### Возможности
- Просмотр каталога, цены, описание, фото
- Корзина и оформление заказа
- Оптовые скидки (цена от N штук)
- Сохранение контактов пользователя
- Админ-команды: добавление/редактирование/удаление товаров, рассылки, просмотр заказов

### Технологии
- Aiogram 3, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic, Loguru
- PostgreSQL

### Старт
1. Скопируйте переменные окружения:
```bash
cp .env.example .env
```
2. Заполните `BOT_TOKEN`, `DATABASE_URL`, при необходимости `ADMIN_IDS`.
3. Активируйте venv и установите зависимости:
```bash
source venv/bin/activate
pip install -r <(python - <<'PY'
print('\n'.join([
    'aiogram==3.6.0',
    'uvloop==0.19.0',
    'python-dotenv==1.0.1',
    'SQLAlchemy==2.0.34',
    'asyncpg==0.29.0',
    'alembic==1.13.2',
    'pydantic==2.7.4',
    'pydantic-settings==2.3.4',
    'loguru==0.7.2',
]))
PY
)
```
4. Запуск бота:
```bash
python -m app.main
```

### Структура
```
app/
  bot/handlers/{user,admin}
  bot/keyboards
  core (настройки)
  db (сессия)
  models (User, Product, Category, Order, OrderItem)
  repositories (DAL)
  schemas (pydantic)
  utils
  main.py
```

