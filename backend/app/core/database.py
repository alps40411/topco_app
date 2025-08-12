# backend/app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .config import settings

# 建立異步資料庫引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# 建立異步 Session 工廠
AsyncSessionFactory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,

)

async def get_db() -> AsyncSession:
    """
    FastAPI 依賴注入，為每個請求提供一個資料庫 session。
    """
    async_session = AsyncSessionFactory()
    try:
        yield async_session
    finally:
        await async_session.close()

async def get_db_session() -> AsyncSession:
    """
    直接獲取資料庫 session，用於非依賴注入的場景。
    記得要手動關閉 session。
    """
    return AsyncSessionFactory()