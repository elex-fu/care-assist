from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as aioredis
import os

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://care:carepass@localhost:3306/care_assist")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# Redis connection pool for WebSocket state sharing + rate limiting
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_pool = aioredis.ConnectionPool.from_url(REDIS_URL, max_connections=50)
