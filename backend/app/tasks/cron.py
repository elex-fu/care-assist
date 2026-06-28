from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.core.reminder_engine import ReminderEngine
from app.db.session import DATABASE_URL
from app.models.medication import Medication
from app.services.medication_log_service import MedicationLogService
from app.tasks.utils import run_async_task


def _task_session():
    """Create a fresh engine/session bound to the current event loop.

    Celery workers may run tasks on different loops than the global
    ``async_session`` was created on. A dedicated engine avoids "Future
    attached to a different loop" errors.
    """
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        echo=False,
    )
    return engine, async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def generate_medication_logs_async() -> dict:
    """Generate pending MedicationLog entries for active medications."""
    engine, session_maker = _task_session()
    async with session_maker() as db:
        result = await db.execute(
            select(Medication.member_id)
            .where(Medication.status == "active")
            .distinct()
        )
        member_ids = result.scalars().all()
        today = date.today()
        end = today + timedelta(days=7)
        total = 0
        for member_id in member_ids:
            total += await MedicationLogService.generate_for_range(
                db, member_id, today, end
            )
    await engine.dispose()
    return {"generated": total}


@celery_app.task(
    name="care_assist.generate_medication_logs",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def generate_medication_logs(self) -> dict:
    try:
        count = run_async_task(generate_medication_logs_async())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return {"generated": count["generated"]}


async def scan_missed_medications_async() -> dict:
    """Scan for missed medication doses and create reminders."""
    engine, session_maker = _task_session()
    async with session_maker() as db:
        count = await ReminderEngine.scan_missed_medications(db)
    await engine.dispose()
    return {"scanned": count, "missed": count}


@celery_app.task(
    name="care_assist.scan_missed_medications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_missed_medications(self) -> dict:
    try:
        result = run_async_task(scan_missed_medications_async())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return result


async def scan_overdue_vaccines_async() -> dict:
    """Scan for overdue vaccine records and create reminders."""
    engine, session_maker = _task_session()
    async with session_maker() as db:
        count = await ReminderEngine.scan_overdue_vaccines(db)
    await engine.dispose()
    return {"scanned": count, "overdue": count}


@celery_app.task(
    name="care_assist.scan_overdue_vaccines",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_overdue_vaccines(self) -> dict:
    try:
        result = run_async_task(scan_overdue_vaccines_async())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return result


async def scan_overdue_reminders_async() -> dict:
    """Mark pending reminders whose scheduled date has passed as overdue."""
    engine, session_maker = _task_session()
    async with session_maker() as db:
        count = await ReminderEngine.scan_overdue_reminders(db)
    await engine.dispose()
    return {"scanned": count, "updated": count}


@celery_app.task(
    name="care_assist.scan_overdue_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_overdue_reminders(self) -> dict:
    try:
        result = run_async_task(scan_overdue_reminders_async())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return result
