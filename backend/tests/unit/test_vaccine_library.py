import pytest
from sqlalchemy import delete

from app.db.seed import VACCINE_LIBRARY_SEED, seed_vaccine_library
from app.models.vaccine_library import VaccineLibrary


@pytest.mark.asyncio
async def test_seed_vaccine_library(db):
    # Clear existing rows within this test transaction so the assertion is
    # deterministic regardless of execution order.
    await db.execute(delete(VaccineLibrary))

    count = await seed_vaccine_library(db)
    assert count == len(VACCINE_LIBRARY_SEED)

    count2 = await seed_vaccine_library(db)
    assert count2 == 0


def test_vaccine_library_defaults():
    entry = VaccineLibrary(
        name="测试疫苗",
        dose_number=1,
        recommended_age_months=0,
        category="测试",
    )
    assert entry.dose_number == 1
    assert entry.description is None
