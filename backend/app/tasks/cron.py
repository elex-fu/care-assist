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


@celery_app.task(
    name="care_assist.generate_medication_logs",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def generate_medication_logs(self) -> dict:
    async def _run():
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
        return total

    try:
        count = run_async_task(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return {"generated": count}


@celery_app.task(
    name="care_assist.scan_missed_medications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_missed_medications(self) -> dict:
    async def _run():
        engine, session_maker = _task_session()
        async with session_maker() as db:
            count = await ReminderEngine.scan_missed_medications(db)
        await engine.dispose()
        return count

    try:
        count = run_async_task(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return {"scanned": count, "missed": count}


@celery_app.task(
    name="care_assist.scan_overdue_vaccines",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_overdue_vaccines(self) -> dict:
    async def _run():
        engine, session_maker = _task_session()
        async with session_maker() as db:
            count = await ReminderEngine.scan_overdue_vaccines(db)
        await engine.dispose()
        return count

    try:
        count = run_async_task(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return {"scanned": count, "overdue": count}


@celery_app.task(
    name="care_assist.scan_overdue_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def scan_overdue_reminders(self) -> dict:
    async def _run():
        engine, session_maker = _task_session()
        async with session_maker() as db:
            count = await ReminderEngine.scan_overdue_reminders(db)
        await engine.dispose()
        return count

    try:
        count = run_async_task(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return {"scanned": count, "updated": count}
