import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.core.config import settings
from app.db.session import engine, Base
from sqlalchemy.ext.asyncio import AsyncEngine
from app.bot.handlers.user.catalog import router as user_router
from app.bot.handlers.admin.products import router as admin_router
from app.bot.handlers.admin.reviews import router as admin_reviews_router
from app.bot.handlers.admin.branding import router as admin_branding_router
from app.bot.handlers.admin.managers import router as admin_managers_router


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")


async def main() -> None:
    setup_logging()
    # ensure DB is up and metadata loaded; create tables if not exist
    async def _init_db(db_engine: AsyncEngine) -> None:
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    await _init_db(engine)

    async with Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    ) as bot:
        dp = Dispatcher()
        dp.include_routers(user_router, admin_router, admin_reviews_router, admin_branding_router, admin_managers_router)
        logger.info("Bot started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
