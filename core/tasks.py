from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import BusLocation

@shared_task
def delete_old_gps_data():
    try:
        cutoff_date = timezone.now() - timedelta(days=7) # ৭ দিন আগের ডাটা
        deleted_count, _ = BusLocation.objects.filter(timestamp__lt=cutoff_date).delete()
        return f"Cleanup Successful: Deleted {deleted_count} old records."
    except Exception as e:
        return f"Cleanup Failed: {e}"