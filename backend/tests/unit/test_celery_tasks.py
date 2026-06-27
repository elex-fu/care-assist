def test_celery_tasks_importable(db_engine):
    # db_engine ensures all model tables exist for the Celery task to query.
    from app.tasks.cron import scan_overdue_reminders

    result = scan_overdue_reminders.run()
    assert isinstance(result["scanned"], int)


def test_celery_app_beat_schedule():
    from app.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "scan-overdue-reminders" in schedule
    assert "scan-missed-medications" in schedule
    assert "scan-overdue-vaccines" in schedule
    assert "generate-medication-logs" in schedule


def test_celery_app_ack_config():
    from app.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_celery_tasks_retry_config(db_engine):
    import inspect

    from app.tasks.cron import (
        generate_medication_logs,
        scan_missed_medications,
        scan_overdue_reminders,
        scan_overdue_vaccines,
    )

    for task in (
        generate_medication_logs,
        scan_missed_medications,
        scan_overdue_vaccines,
        scan_overdue_reminders,
    ):
        assert inspect.ismethod(task.__wrapped__) is True
        assert task.max_retries == 3
        assert task.default_retry_delay == 60
        assert Exception in task.autoretry_for
