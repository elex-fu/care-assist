import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import init_db
from app.models.vaccine_library import VaccineLibrary


@pytest.mark.asyncio
async def test_init_db_seeds_vaccine_library(db: AsyncSession):
    """Calling init_db creates tables and populates vaccine_library."""
    await init_db()
    result = await db.execute(select(VaccineLibrary))
    rows = result.scalars().all()
    assert len(rows) > 0
