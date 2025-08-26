from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
	pass


def create_engine() -> AsyncEngine:
	return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


engine: AsyncEngine = create_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
	bind=engine,
	expire_on_commit=False,
)


