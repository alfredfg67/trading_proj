from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

def get_engine_with_retry(retries=3, delay=1):
    for attempt in range(retries):
        try:
            engine = create_async_engine(
                settings.DATABASE_URL,
                echo=True,
                connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
            )
            return engine
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt+1} failed: {e}")
            asyncio.run(asyncio.sleep(delay))
    raise Exception("Could not connect to database after multiple attempts")

engine = get_engine_with_retry()
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session