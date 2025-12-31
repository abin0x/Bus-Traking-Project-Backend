from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Bus, BusLocation
from .services import BusTrackingService
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_bus_location_task(bus_id, lat, lng, speed, direction, api_key):
    """ভারী বিজনেস লজিক ব্যাকগ্রাউন্ডে রান করার জন্য টাস্ক"""
    try:
        # ১. ডাটাবেস থেকে বাস অবজেক্ট নেওয়া
        bus_obj = Bus.objects.select_related('route').prefetch_related('route__stops').get(device_id=bus_id)
        
        # ২. সিকিউরিটি চেক (ব্যাকগ্রাউন্ডে পুনরায় ভ্যালিডেশন)
        if bus_obj.api_key != api_key:
            return f"Error: Invalid API Key for {bus_id}"

        # ৩. সার্ভিস লেয়ার কল করা
        BusTrackingService.handle_location_update(
            bus_obj=bus_obj, lat=lat, lng=lng, speed=speed, device_direction=direction
        )
        return f"Successfully processed location for {bus_id}"
        
    except Bus.DoesNotExist:
        return f"Error: Bus {bus_id} not found"
    except Exception as e:
        logger.error(f"Async Task Failed for {bus_id}: {e}")
        return f"Failed: {str(e)}"
    
@shared_task
def delete_old_gps_data():
    try:
        cutoff_date = timezone.now() - timedelta(days=7) # ৭ দিন আগের ডাটা
        deleted_count, _ = BusLocation.objects.filter(timestamp__lt=cutoff_date).delete()
        return f"Cleanup Successful: Deleted {deleted_count} old records."
    except Exception as e:
        return f"Cleanup Failed: {e}"