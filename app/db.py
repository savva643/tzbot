import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

# управление бд


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    return create_async_engine(settings.db_url, echo=False, future=True)


def get_session_factory(engine=None):
    engine = engine or get_engine()
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine=None):
    from .models import Message, User  

    engine = engine or get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)









def init_db_sync(engine=None):
    asyncio.run(init_db(engine))
