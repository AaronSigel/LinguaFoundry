"""Database engine and session helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.database_echo)
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for dependency injection."""

    async with async_session_factory() as session:
        yield session
