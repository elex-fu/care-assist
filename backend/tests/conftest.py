import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://care:carepass@localhost:3307/care_assist")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DEBUG", "true")

from app.main import app as fastapi_app
from app.db.session import Base, async_session
from app.models.member import Member
from app.models.family import Family
from app.models.indicator import IndicatorData
from app.core.security import create_jwt

# Ensure all models are registered in Base.metadata before creating tables
import app.models  # noqa: F401


TEST_ENGINE = create_async_engine(
    os.environ["DATABASE_URL"],
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    echo=False,
)
TestSession = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield TEST_ENGINE
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await TEST_ENGINE.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db(db_engine):
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_engine):
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def test_family(db):
    import secrets
    family = Family(
        id=str(uuid.uuid4()),
        name="测试家庭",
        invite_code=secrets.token_urlsafe(8)[:6].upper(),
    )
    db.add(family)
    await db.commit()
    await db.refresh(family)
    return family


@pytest_asyncio.fixture(loop_scope="session")
async def test_creator(db, test_family):
    member = Member(
        id=str(uuid.uuid4()),
        family_id=test_family.id,
        name="测试创建者",
        gender="male",
        type="adult",
        role="creator",
        wx_openid=f"mock_openid_{uuid.uuid4().hex[:16]}",
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@pytest_asyncio.fixture(loop_scope="session")
async def test_member(db, test_family):
    member = Member(
        id=str(uuid.uuid4()),
        family_id=test_family.id,
        name="测试成员",
        gender="female",
        type="child",
        role="member",
        wx_openid=f"mock_openid_{uuid.uuid4().hex[:16]}",
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@pytest_asyncio.fixture(loop_scope="session")
async def auth_client(client, test_creator):
    token = create_jwt(str(test_creator.id), token_type="access")
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]


@pytest_asyncio.fixture(loop_scope="session")
async def member_client(client, test_member):
    token = create_jwt(str(test_member.id), token_type="access")
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]
