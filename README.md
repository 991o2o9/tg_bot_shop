# Shop Bot

A Telegram bot for product catalog management, shopping cart functionality, order processing, and admin panel operations through bot commands.

## Features

### User Features
- **Product Catalog**: Browse products with prices, descriptions, and photos
- **Shopping Cart**: Add/remove items and place orders
- **Bulk Discounts**: Special pricing for bulk quantities (price from N items)
- **Contact Management**: Save user contact information for orders
- **Order Tracking**: View order history and status

### Admin Features
- **Product Management**: Add, edit, and delete products
- **Order Management**: View and manage customer orders
- **Broadcasting**: Send messages to all users
- **Branding**: Customize bot appearance and messages
- **Review Management**: Manage product reviews

## Technologies

- **Bot Framework**: Aiogram 3.6.0
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async, asyncpg)
- **Migrations**: Alembic
- **Validation**: Pydantic
- **Logging**: Loguru
- **Async Runtime**: uvloop (Linux/macOS)

## Project Structure

```
shop-bot/
├── app/
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── admin/          # Admin command handlers
│   │   │   │   ├── branding.py
│   │   │   │   ├── products.py
│   │   │   │   └── reviews.py
│   │   │   └── user/           # User command handlers
│   │   │       └── catalog.py
│   │   ├── keyboards/          # Inline keyboards
│   │   ├── middlewares/        # Custom middlewares
│   │   └── services/           # Business logic services
│   ├── core/
│   │   └── config.py          # App configuration
│   ├── db/
│   │   └── session.py         # Database session management
│   ├── models/                # SQLAlchemy models
│   │   ├── branding.py
│   │   ├── order.py
│   │   ├── product.py
│   │   ├── review.py
│   │   └── user.py
│   ├── repositories/          # Data access layer
│   ├── schemas/               # Pydantic schemas
│   ├── utils/                 # Utility functions
│   └── main.py               # Application entry point
├── migrations/                # Alembic migrations
├── scripts/                   # Utility scripts
├── tests/                     # Test files
└── pyproject.toml            # Poetry configuration
```

## Quick Start

### Prerequisites

- Python 3.10-3.12
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shop-bot
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables in `.env`**
   ```env
   BOT_TOKEN=your_telegram_bot_token
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shop_bot
   ADMIN_IDS=123456789,987654321  # Optional: Comma-separated admin user IDs
   ```

4. **Install dependencies**

   **Using Poetry (recommended):**
   ```bash
   poetry install
   poetry shell
   ```

   **Using pip:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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

5. **Set up database**
   ```bash
   # Run migrations
   alembic upgrade head
   ```

6. **Start the bot**
   ```bash
   python -m app.main
   ```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram Bot API token | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `ADMIN_IDS` | Comma-separated admin user IDs | No | - |
| `DEBUG` | Enable debug mode | No | `False` |

### Database Configuration

The bot uses PostgreSQL with async SQLAlchemy. Make sure your database URL follows this format:
```
postgresql+asyncpg://username:password@host:port/database_name
```

## Development

### Running Tests
```bash
# Using Poetry
poetry run pytest

# Using pip
pytest
```

### Code Formatting
```bash
# Using Poetry
poetry run ruff check .
poetry run ruff format .

# Using pip
ruff check .
ruff format .
```

### Database Migrations

**Create a new migration:**
```bash
alembic revision --autogenerate -m "description"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migration:**
```bash
alembic downgrade -1
```

## Usage

### User Commands
- `/start` - Start the bot and see the main menu
- Browse catalog through inline keyboards
- Add items to cart and place orders

### Admin Commands
- Product management through bot interface
- Order management and tracking
- User broadcasting capabilities
- Branding customization

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the maintainers

---

**Note**: Make sure to keep your bot token and database credentials secure. Never commit them to version control.