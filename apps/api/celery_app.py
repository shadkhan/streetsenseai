from celery import Celery

from config import settings

celery = Celery(
    "streetsense",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.ingest", "tasks.risk_tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/London",
    enable_utc=True,
    beat_schedule={
        # SM-001: poll Street Manager SQS queue for new work events
        "poll-sm-sqs-every-30s": {
            "task": "tasks.ingest.poll_sm_sqs",
            "schedule": 30.0,
        },
        # SM-005: REST polling fallback — catches any permits missed by webhooks/SQS
        "poll-sm-rest-every-15min": {
            "task": "tasks.ingest.poll_sm_rest",
            "schedule": 900.0,
        },
        # CR-003/004: Re-score all corridors every hour so list endpoint stays fresh
        "score-corridors-every-hour": {
            "task": "tasks.risk_tasks.score_all_corridors",
            "schedule": 3600.0,
        },
    },
)
