from celery import shared_task
from django.utils import timezone
from .models import Monitor, Snapshot
from .services.scraper import Scraper
from .services.hash import generate_hash
from django.shortcuts import get_object_or_404
import time
from datetime import timedelta
from django.utils import timezone
from celery.schedules import crontab

@shared_task
def check_url():
    for i in range(10):
        print(i)
        time.sleep(1)

@shared_task
def check_monitor(monitor_id, user_id):
    try:
        monitor = Monitor.objects.get(
            id=monitor_id,
            status=True,
            user=user_id
        )
    except Monitor.DoesNotExist:
        return {"status": "skipped", "reason": "Monitor not found or inactive"}

    scraper = Scraper()
    result = scraper.validate_url(monitor.url)

    if not result["valid"]:
        return {
            "status": "failed",
            "monitor_id": monitor.id,
            "reason": result["reason"],
        }
    
    content = result["content"]
    new_hash = generate_hash(content)

    if new_hash == monitor.last_hash:
        monitor.last_check = timezone.now()
        monitor.save(update_fields=["last_check"])

        return {
            "status": "unchanged",
            "monitor_id": monitor.id,
        }
    
    Snapshot.objects.create(
        monitor=monitor,
        content=content,
        content_hash=new_hash,
    )

    monitor.last_hash = new_hash
    monitor.last_check = timezone.now()
    monitor.save(update_fields=["last_hash", "last_check"])

    return {
        "status": "changed",
        "monitor_id": monitor.id,
    }


@shared_task
def schedule_due_monitors():
    now = timezone.now()

    monitors = Monitor.objects.filter(status=True)

    for monitor in monitors:
        if monitor.last_check is None:
            check_monitor.delay(monitor.id, monitor.user)
            continue

        next_check = monitor.last_check + timedelta(
            minutes=monitor.check_interval
        )

        if now >= next_check:  
            check_monitor.delay(monitor.id, monitor.user_id)